import unohelper
from inlay_object import Factory, FACTORY

g_ImplementationHelper=unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Factory,FACTORY,(FACTORY,))
