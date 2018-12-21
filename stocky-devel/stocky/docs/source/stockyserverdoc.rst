Stocky Server Documentation
***************************

Module Overview
===============

 .. snakenibbles::
    :source_directory: /stockysrc 
    :infiles: ./*.py serverlib
    :outstub: overview
    :exclude: test


Module serverlib.stockyserver
================================

.. scopyreverse:: /stockysrc/serverlib/stockyserver
    :gooly:
    :bla:

.. automodule:: serverlib.stockyserver
	:members:
	:show-inheritance:

Module serverlib.ServerWebSocket
================================

.. scopyreverse:: /stockysrc/serverlib/ServerWebSocket
    :gooly:
    :bla:

.. automodule:: serverlib.ServerWebSocket
	:members:
	:show-inheritance:

Module serverlib.Taskmeister
============================

.. scopyreverse:: /stockysrc/serverlib/Taskmeister
    :gooly:
    :bla:
.. automodule:: serverlib.Taskmeister
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_taskmeister.py
   :tabletitle: The Taskmeister unit test results

	   
Module serverlib.yamlutil
=========================
.. scopyreverse:: /stockysrc/serverlib/yamlutil
    :gooly:
    :bla:
.. automodule:: serverlib.yamlutil
	:members:
	:show-inheritance:
	   
.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_yamlutil.py
	      


Module serverlib.serverconfig
=============================
.. scopyreverse:: /stockysrc/serverlib/serverconfig
    :gooly:
    :bla:
.. automodule:: serverlib.serverconfig
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_serverconfig.py
	      
	   
Module ChemStok.ChemStock
===========================
.. scopyreverse:: /stockysrc/serverlib/ChemStock
    :gooly:
    :bla:

.. uml:: chemstock.plantuml
   :scale: 50%
   :caption: The database schema of the sqlalchemy database implemented in ChemStock.

.. automodule:: serverlib.ChemStock
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/chemstocktest.yaml
   :testfile: test_ChemStock.py
   :testclass: Test_Chemstock_NOQAI
   :tabletitle: ChemStock tests that do not access QAI

		
.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_ChemStock.py
   :testclass: Test_Chemstock_EMPTYDB
   :tabletitle: ChemStock tests that are performed on an empty database

		
.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_ChemStock.py
   :testclass: Test_funcs
   :tabletitle: Tests of helper functions in ChemStock
		
.. pytesttable::
   :testresultfile: /stockysrc/chemstockqaitest.yaml
   :testfile: test_ChemStock.py
   :testclass: Test_Chemstock_WITHQAI
   :tabletitle: ChemStock tests that access a QAI server

		
Module serverlib.commlink
=========================
.. scopyreverse:: /stockysrc/serverlib/commlink
    :gooly:
    :bla:
.. automodule:: serverlib.commlink
	:members:
	:show-inheritance:
	   
.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_commlink.py

	      
Module serverlib.timelib
=========================
.. scopyreverse:: /stockysrc/serverlib/timelib
    :gooly:
    :bla:
.. automodule:: serverlib.timelib
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_timelib.py

Module serverlib.TLSAscii
=========================
.. scopyreverse:: /stockysrc/serverlib/TLSAscii
    :gooly:
    :bla:
.. automodule:: serverlib.TLSAscii
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_TLSAscii.py


Module serverlib.qai_helper
===========================
.. scopyreverse:: /stockysrc/serverlib/qai_helper
    :gooly:
    :bla:
.. automodule:: serverlib.qai_helper
	:members:
	:show-inheritance:

.. pytesttable::
   :testresultfile: /stockysrc/alltest.yaml
   :testfile: test_qai_helper.py
   :tabletitle: qai_helper tests without server access

.. pytesttable::
   :testresultfile: /stockysrc/qaitest.yaml
   :testfile: test_qai_helper.py
   :tabletitle: qai_helper tests with server access		
