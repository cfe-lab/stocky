Stocky Webclient Documentation
******************************
This is the documentation of the Stocky webclient.

 .. snakenibbles::
    :source_directory: /stockysrc/webclient
    :infiles: ./*.py
    :outstub: wcoverview
    :exclude: test


Module webclient
================
The webclient directory contains all modules and code specific to the webclient.
The webclient makes extensive use of code resourses in the qailib/transcryptlib directory.

The main web client program is shown here:

.. literalinclude:: ../../webclient/webclient.py
    :language: python

There is another main program created for demonstration and testing purposes defined in
rfidpingtest.py:

.. literalinclude:: ../../webclient/rfidpingtest.py
    :language: python

	       
Module commonmsg
----------------

.. scopyreverse:: /stockysrc/webclient/commonmsg.py
    :gooly:
    :bla:

.. automodule:: webclient.commonmsg
	:members:
	:show-inheritance:

Module wccontroller
-------------------

.. scopyreverse:: /stockysrc/webclient/wccontroller.py
    :gooly:
    :bla:

.. automodule:: webclient.wccontroller
	:members:
	:show-inheritance:

Module wcstatus
---------------

.. scopyreverse:: /stockysrc/webclient/wcstatus.py
    :gooly:
    :bla:

.. automodule:: webclient.wcstatus
	:members:
	:show-inheritance:


Module wcviews
--------------

.. scopyreverse:: /stockysrc/webclient/wcviews.py
    :gooly:
    :bla:

.. automodule:: webclient.wcviews
	:members:
	:show-inheritance:

	   
Module qailib.common
====================
This directory contains modules containing foundation classes of the GUI framework,
from which other classes are derived. These modules are designed to be compiled under Cpython
(to make testing easy) as well as to javascript using Transcrypt.


Module qailib.common.base
-------------------------

.. scopyreverse:: /stockysrc/qailib/common/base.py
    :gooly:
    :bla:

.. automodule:: qailib.common.base
	:members:
	:show-inheritance:

Module qailib.common.serversocketbase
-------------------------------------

.. scopyreverse:: /stockysrc/qailib/common/serversocketbase.py
    :gooly:
    :bla:

.. automodule:: qailib.common.serversocketbase
	:members:
	:show-inheritance:
       
Module qailib.transcryptlib
===========================

Module qailib.transcryptlib.cleverlabels
----------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/cleverlabels.py
    :gooly:
    :bla:

.. automodule:: qailib.transcryptlib.cleverlabels
	:members:
	:show-inheritance:

Module qailib.transcryptlib.forms
---------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/forms.py
    :gooly:
    :bla:

.. automodule:: qailib.transcryptlib.forms
	:members:
	:show-inheritance:


Module qailib.transcryptlib.genutils
------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/genutils.py
    :gooly:
    :bla:

.. automodule:: qailib.transcryptlib.genutils
	:members:
	:show-inheritance:
       

Module qailib.transcryptlib.htmlelements
----------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/htmlelements.py
    :gooly:
    :bla:
       
.. automodule:: qailib.transcryptlib.htmlelements
	:members:
	:show-inheritance:

Module qailib.transcryptlib.serversocket
----------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/serversocket.py
    :gooly:
    :bla:
       
.. automodule:: qailib.transcryptlib.serversocket
	:members:
	:show-inheritance:

Module qailib.transcryptlib.simpletable
---------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/simpletable.py
    :gooly:
    :bla:
       
.. automodule:: qailib.transcryptlib.simpletable
	:members:
	:show-inheritance:

Module qailib.transcryptlib.SVGlib
----------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/SVGlib.py
    :gooly:
    :bla:

.. automodule:: qailib.transcryptlib.SVGlib
	:members:
	:show-inheritance:


Module qailib.transcryptlib.websocket
-------------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/websocket.py
    :gooly:
    :bla:
  
.. automodule:: qailib.transcryptlib.websocket
	:members:
	:show-inheritance:
       
Module qailib.transcryptlib.widgets
-----------------------------------

.. scopyreverse:: /stockysrc/qailib/transcryptlib/widgets.py
    :gooly:
    :bla:
       
.. automodule:: qailib.transcryptlib.widgets
	:members:
	:show-inheritance:



