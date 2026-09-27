"""Writer commands for native Inlay diagram objects."""
import uuid
from pathlib import Path
import uno
import unohelper
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo
from inlay_object import CLASS_ID, parse_png

IMPLEMENTATION='org.inlay.WriterHandler'
PROTOCOL='org.inlay.writer:'


def prop(name,value):
    p=uno.createUnoStruct('com.sun.star.beans.PropertyValue');p.Name=name;p.Value=value;return p


def current_object(doc):
    obj=doc.CurrentController.Selection
    if hasattr(obj,'getCount') and obj.getCount()==1:obj=obj.getByIndex(0)
    if not hasattr(obj,'supportsService') or not obj.supportsService('com.sun.star.text.TextEmbeddedObject'):
        raise ValueError('Select an Inlay diagram object first.')
    embedded=obj.getExtendedControlOverEmbeddedObject()
    if bytes(embedded.getClassID())!=uuid.UUID(CLASS_ID).bytes:
        raise ValueError('This is not an Inlay diagram.')
    return embedded


class Handler(unohelper.Base,XInitialization,XDispatchProvider,XDispatch,XServiceInfo):
    def __init__(self,ctx):self.ctx=ctx;self.frame=None
    def initialize(self,args):
        if args:self.frame=args[0]
    def getImplementationName(self):return IMPLEMENTATION
    def getSupportedServiceNames(self):return ('com.sun.star.frame.ProtocolHandler',)
    def supportsService(self,name):return name in self.getSupportedServiceNames()
    def queryDispatch(self,url,target,flags):
        return self if url.Protocol==PROTOCOL and url.Path in ('insert','import','edit','export') else None
    def queryDispatches(self,requests):return tuple(self.queryDispatch(r.FeatureURL,r.FrameName,r.SearchFlags) for r in requests)
    def addStatusListener(self,listener,url):
        event=uno.createUnoStruct('com.sun.star.frame.FeatureStateEvent')
        event.Source=self;event.FeatureURL=url;event.IsEnabled=True;listener.statusChanged(event)
    def removeStatusListener(self,*args):pass
    def choose_file(self,save=False):
        picker=self.ctx.ServiceManager.createInstanceWithContext('com.sun.star.ui.dialogs.FilePicker',self.ctx)
        picker.initialize((1 if save else 0,))
        picker.appendFilter('Inlay PNG diagrams','*.png');picker.setCurrentFilter('Inlay PNG diagrams')
        try:
            if picker.execute():return Path(uno.fileUrlToSystemPath(picker.getFiles()[0]))
        finally:picker.dispose()
        return None
    def dispatch(self,url,args):
        try:
            doc=self.frame.Controller.Model
            if not doc.supportsService('com.sun.star.text.TextDocument'):raise ValueError('Open a Writer document.')
            if url.Path=='export':
                component=current_object(doc).getComponent();path=self.choose_file(True)
                if path:path.write_bytes(bytes(component.getPropertyValue('PNG')))
                return
            if doc.isReadonly():raise ValueError('The document is read-only.')
            if url.Path=='edit':current_object(doc).doVerb(0);return
            data=None
            if url.Path=='import':
                path=self.choose_file()
                if path is None:return
                data=path.read_bytes();parse_png(data)
            manager=doc.getUndoManager();manager.enterUndoContext('Insert Inlay diagram')
            try:
                obj=doc.createInstance('com.sun.star.text.TextEmbeddedObject')
                obj.CLSID=CLASS_ID
                obj.AnchorType=uno.Enum('com.sun.star.text.TextContentAnchorType','AS_CHARACTER')
                cursor=doc.CurrentController.ViewCursor
                cursor.Text.insertTextContent(cursor,obj,False)
                embedded=obj.getExtendedControlOverEmbeddedObject()
                if embedded is None:raise ValueError('Cannot create the Inlay object. Check the extension installation.')
                if data is not None:embedded.getComponent().setPropertyValue('PNG',uno.ByteSequence(data))
                doc.CurrentController.select(obj)
            finally:manager.leaveUndoContext()
            if url.Path=='insert':embedded.doVerb(0)
        except Exception as error:self.message(str(error))
    def message(self,text):
        toolkit=self.ctx.ServiceManager.createInstanceWithContext('com.sun.star.awt.Toolkit',self.ctx)
        box=toolkit.createMessageBox(self.frame.ContainerWindow,uno.Enum('com.sun.star.awt.MessageBoxType','INFOBOX'),1,'Inlay',text)
        box.execute()


g_ImplementationHelper=unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Handler,IMPLEMENTATION,('com.sun.star.frame.ProtocolHandler',))
