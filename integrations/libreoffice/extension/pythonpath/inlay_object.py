"""Native Inlay embedded object: storage, visual representation and activation."""
import json
from pathlib import Path
import struct
import uuid
import uno
import unohelper
from com.sun.star.embed import XEmbeddedObject, XEmbedPersist, XEmbedObjectCreator, XEmbedObjectFactory
from com.sun.star.lang import XServiceInfo, XComponent
from com.sun.star.container import XChild
from com.sun.star.util import XModifiable, XCloseable
from com.sun.star.beans import XPropertySet, XPropertySetInfo
from inlay_png import chunks, recover
import tempfile

CLASS_ID = 'A3299102-761D-48D5-A881-784269D7D480'
MIME = 'application/vnd.inlay.diagram'
FACTORY = 'org.inlay.EmbeddedFactory'


def value(args, name, default=None):
    return next((p.Value for p in args if p.Name == name), default)


def read_stream(storage, name):
    stream=storage.openStreamElement(name, 1)
    inp=stream.getInputStream()
    try:
        out=[]
        while True:
            count,data=inp.readBytes(None, 65536)
            if not count: break
            out.append(bytes(data))
        return b''.join(out)
    finally: inp.closeInput()


def write_stream(storage, name, data):
    stream=storage.openStreamElement(name, 4 | 8)
    out=stream.getOutputStream()
    try: out.writeBytes(uno.ByteSequence(data)); out.closeOutput()
    finally: stream.dispose()


def parse_png(data):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        f.write(data); f.flush()
        parts=chunks(f.name)
        source=recover(parts).decode('utf8')
    from inlay_png import text_field
    fields={}
    for kind,payload,_ in parts:
        if kind in (b'iTXt',b'tEXt',b'zTXt'):
            k,v=text_field(kind,payload);fields[k]=v
    typ=fields.get(b'SourceType') or json.loads(fields.get(b'SourceManifest','{}')).get('source_type','unknown')
    return source,typ


class PropertyInfo(unohelper.Base, XPropertySetInfo):
    def getProperties(self):
        result=[]
        for name,typ in [('ObjectIdentity','string'),('Source','string'),('SourceType','string'),('PNG','[]byte')]:
            p=uno.createUnoStruct('com.sun.star.beans.Property');p.Name=name;p.Type=uno.getTypeByName(typ);p.Attributes=0 if name=='PNG' else 1
            result.append(p)
        return tuple(result)
    def getPropertyByName(self,name):
        for p in self.getProperties():
            if p.Name==name:return p
        raise uno.getClass('com.sun.star.beans.UnknownPropertyException')(name,self)
    def hasPropertyByName(self,name):return name in ('ObjectIdentity','Source','SourceType','PNG')


class Diagram(unohelper.Base, XEmbeddedObject, XEmbedPersist, XChild, XModifiable, XPropertySet, XComponent, XCloseable):
    def __init__(self, ctx):
        self.identity=uuid.uuid4().hex
        self.ctx=ctx;self.storage=None;self.entry='';self.pending=None
        self.state=0;self.client=None;self.parent=None;self.closed=False;self.modified=False
        self.events=[];self.states=[];self.closes=[];self.modifies=[];self.disposals=[]
        self.size=uno.createUnoStruct('com.sun.star.awt.Size');self.size.Width=14000;self.size.Height=5500
        self.png=(Path(__file__).parent/'default.png').read_bytes()
        self.source,self.source_type=parse_png(self.png)
        width,height=struct.unpack('>II',self.png[16:24])
        self.size.Height=max(500,round(self.size.Width*height/width))
        self.session=None

    def check(self):
        if self.closed:raise uno.getClass('com.sun.star.lang.DisposedException')('Diagram is closed',self)

    def getPropertySetInfo(self):return PropertyInfo()
    def getPropertyValue(self,name):
        self.check()
        if name=='ObjectIdentity':return self.identity
        if name=='Source':return self.source
        if name=='SourceType':return self.source_type
        if name=='PNG':return uno.ByteSequence(self.png)
        raise uno.getClass('com.sun.star.beans.UnknownPropertyException')(name,self)
    def setPropertyValue(self,name,data):
        self.check()
        if self.isReadonly():raise uno.getClass('com.sun.star.beans.PropertyVetoException')('Read-only diagram',self)
        if name!='PNG':raise uno.getClass('com.sun.star.beans.PropertyVetoException')('Read-only property',self)
        raw=bytes(data);source,typ=parse_png(raw)
        self.png,self.source,self.source_type=raw,source,typ
        self.setModified(True);self.update()
    def addPropertyChangeListener(self,*args):pass
    def removePropertyChangeListener(self,*args):pass
    def addVetoableChangeListener(self,*args):pass
    def removeVetoableChangeListener(self,*args):pass

    def getClassID(self):return uno.ByteSequence(uuid.UUID(CLASS_ID).bytes)
    def getClassName(self):return 'Inlay Diagram'
    def setClassInfo(self,*args):pass
    def getComponent(self):return self
    def getParent(self):return self.parent
    def setParent(self,parent):self.parent=parent
    def setClientSite(self,client):self.client=client
    def getClientSite(self):return self.client
    def getCurrentState(self):return self.state
    def getReachableStates(self):return (0,1)
    def changeState(self,new):
        self.check()
        if new not in (0,1):raise uno.getClass('com.sun.star.embed.UnreachableStateException')('External editor only',self)
        old=self.state
        if old==new:return
        event=uno.createUnoStruct('com.sun.star.lang.EventObject');event.Source=self
        for listener in tuple(self.states):listener.changingState(event,old,new)
        self.state=new
        for listener in tuple(self.states):listener.stateChanged(event,old,new)
    def addStateChangeListener(self,l):self.states.append(l)
    def removeStateChangeListener(self,l):
        if l in self.states:self.states.remove(l)
    def doVerb(self,verb):
        self.check()
        if verb==-3:return
        if verb not in (0,-1,-2):raise ValueError('Unsupported Inlay verb')
        from inlay_session import edit_object
        edit_object(self)
    def getSupportedVerbs(self):
        v=uno.createUnoStruct('com.sun.star.embed.VerbDescriptor');v.VerbID=0;v.VerbName='Edit in Inlay';v.VerbFlags=0;v.VerbAttributes=2
        return (v,)
    def setContainerName(self,name):self.container_name=name
    def setUpdateMode(self,mode):self.update_mode=mode
    def getStatus(self,aspect):return 512 | 16384
    def setVisualAreaSize(self,aspect,size):self.size=size
    def getVisualAreaSize(self,aspect):return self.size
    def getMapUnit(self,aspect):return 0
    def getPreferredVisualRepresentation(self,aspect):
        v=uno.createUnoStruct('com.sun.star.embed.VisualRepresentation')
        v.Flavor.MimeType='image/png';v.Flavor.HumanPresentableName='Inlay diagram'
        v.Flavor.DataType=uno.getTypeByName('[]byte');v.Data=uno.ByteSequence(self.png)
        return v
    def update(self):
        event=uno.createUnoStruct('com.sun.star.document.EventObject');event.Source=self;event.EventName='OnVisAreaChanged'
        for listener in tuple(self.events):listener.notifyEvent(event)
    def addEventListener(self,l):
        (self.events if hasattr(l,'notifyEvent') else self.disposals).append(l)
    def removeEventListener(self,l):
        if l in self.events:self.events.remove(l)
        if l in self.disposals:self.disposals.remove(l)
    def isModified(self):return self.modified
    def setModified(self,modified):
        self.modified=modified
        if modified:
            if self.parent is not None:self.parent.setModified(True)
            event=uno.createUnoStruct('com.sun.star.lang.EventObject');event.Source=self
            for listener in tuple(self.modifies):listener.modified(event)
    def addModifyListener(self,l):self.modifies.append(l)
    def removeModifyListener(self,l):
        if l in self.modifies:self.modifies.remove(l)
    def addCloseListener(self,l):self.closes.append(l)
    def removeCloseListener(self,l):
        if l in self.closes:self.closes.remove(l)
    def close(self,ownership):
        if self.closed:return
        e=uno.createUnoStruct('com.sun.star.lang.EventObject');e.Source=self
        for l in tuple(self.closes):l.queryClosing(e,ownership)
        self.closed=True
        for l in tuple(self.closes):l.notifyClosing(e)
        for l in tuple(self.disposals):l.disposing(e)
    def dispose(self):self.close(True)

    def load(self):
        child=self.storage.openStorageElement(self.entry,1)
        try:
            metadata=json.loads(read_stream(child,'diagram.json'))
            if metadata.get('version')!=1:raise ValueError('Unsupported Inlay object version')
            self.png=read_stream(child,'preview.png')
            self.source=read_stream(child,'source.txt').decode('utf8')
            self.source_type=metadata['source_type']
            parsed,typ=parse_png(self.png)
            if parsed!=self.source or typ!=self.source_type:raise ValueError('Inlay source and preview mismatch')
            self.size.Width,self.size.Height=metadata['size']
        finally:child.dispose()
    def store(self,storage,name):
        child=storage.openStorageElement(name,7)
        try:
            child.setPropertyValue('MediaType',MIME)
            write_stream(child,'source.txt',self.source.encode('utf8'))
            write_stream(child,'preview.png',self.png)
            write_stream(child,'diagram.json',json.dumps(dict(version=1,source_type=self.source_type,size=[self.size.Width,self.size.Height])).encode())
            child.commit()
        finally:child.dispose()
    def setPersistentEntry(self,storage,name,mode,media,args):
        self.storage,self.entry=storage,name
        if mode==0 and storage.hasByName(name):self.load()
        elif mode in (0,1,3):
            url=value(media,'URL')
            if url:
                self.png=Path(uno.fileUrlToSystemPath(url)).read_bytes();self.source,self.source_type=parse_png(self.png)
            self.store(storage,name)
    def storeOwn(self):
        self.check();self.store(self.storage,self.entry);self.setModified(False)
    def storeToEntry(self,storage,name,media,args):self.store(storage,name)
    def storeAsEntry(self,storage,name,media,args):
        self.store(storage,name);self.pending=(storage,name)
    def saveCompleted(self,use_new):
        if use_new and self.pending:self.storage,self.entry=self.pending;self.setModified(False)
        self.pending=None
    def hasEntry(self):return self.storage is not None and bool(self.entry)
    def getEntryName(self):return self.entry
    def isReadonly(self):return bool(self.parent is not None and self.parent.isReadonly())
    def reload(self,media,args):self.load();self.update()


class Factory(unohelper.Base, XEmbedObjectCreator, XEmbedObjectFactory, XServiceInfo):
    def __init__(self,ctx):self.ctx=ctx
    def getImplementationName(self):return FACTORY
    def getSupportedServiceNames(self):return (FACTORY,)
    def supportsService(self,name):return name==FACTORY
    def createInstanceUserInit(self,cls,name,storage,entry,mode,media,args):
        obj=Diagram(self.ctx);obj.setPersistentEntry(storage,entry,mode,media,args);return obj
    def createInstanceInitNew(self,cls,name,storage,entry,args):return self.createInstanceUserInit(cls,name,storage,entry,1,(),args)
    def createInstanceInitFromEntry(self,storage,entry,media,args):return self.createInstanceUserInit((),'Inlay Diagram',storage,entry,0,media,args)
    def createInstanceInitFromMediaDescriptor(self,storage,entry,media,args):return self.createInstanceUserInit((),'Inlay Diagram',storage,entry,3,media,args)
