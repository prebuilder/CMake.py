#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest

thisFile = Path(__file__).absolute()
thisDir = thisFile.parent.absolute()
repoMainDir = thisDir.parent.absolute()
sys.path.append(str(repoMainDir))

from collections import OrderedDict
dict=OrderedDict

from CMake import *

class SimpleTests(unittest.TestCase):
	def setUp(self):
		pass
	
	@unittest.skip
	def testSetSimple(self):
		cm = CMakeInterpreter()
		cm.interpret('set(a "b")\n')
		self.assertEqual(cm.ns["a"], "b")
	
	@unittest.skip
	def testSetAssignOther(self):
		cm = CMakeInterpreter()
		cm.interpret('set(a "b")\n')
		cm.interpret('set(c "${a}")\n')
		self.assertEqual(cm.ns["c"], "b")
	
	@unittest.skip
	def testMessage(self):
		class ourBuiltins(cmakeBuiltins):
			@classmethod
			def message(cls, interp, args):
				argz = parseFuncArgs(interp, messageSpec, args)
				print(argz)
		
		cm = CMakeInterpreter(builtins = ourBuiltins)
		cm.interpret('message(STATUS a)')
	
	@unittest.skip
	def testInclude(self):
		ourIncludes = {
			"a": 'set(a "B")\ninclude(b)\n',
			"b": 'set(b "C")\n',
		}
		class ourBuiltins(cmakeBuiltins):
			@classmethod
			def include(cls, interp, args):
				argz = parseFuncArgs(interp, includeSpec, args)
				try:
					interp.interpret(ourIncludes[argz["path"]])
					if argz["RESULT_VARIABLE"]:
						interp.ns[argz["RESULT_VARIABLE"]] = argz["path"]
				except:
					if argz["RESULT_VARIABLE"]:
						interp.ns[argz["RESULT_VARIABLE"]] = argz["RESULT_VARIABLE"]+"-NOTFOUND"
					
					if not argz["OPTIONAL"]:
						raise

		
		cm = CMakeInterpreter(builtins = ourBuiltins)
		cm.interpret('include(a OPTIONAL)')
		self.assertEqual(cm.ns["a"], "B")
		self.assertEqual(cm.ns["b"], "C")
		return
		
		cm.interpret('include(a RESULT_VARIABLE <var>)')
		cm.interpret('include(a NO_POLICY_SCOPE)')
		
		cm = CMakeInterpreter(builtins = ourBuiltins)
		cm.interpret('include(a OPTIONAL NO_POLICY_SCOPE)')
		cm.interpret('include(a RESULT_VARIABLE <var> NO_POLICY_SCOPE)')

		cm = CMakeInterpreter(builtins = ourBuiltins)
		cm.interpret('include(a OPTIONAL RESULT_VARIABLE <var>)')
		cm.interpret('include(a OPTIONAL NO_POLICY_SCOPE)')
		
		cm = CMakeInterpreter(builtins = ourBuiltins)
		cm.interpret('include(a OPTIONAL RESULT_VARIABLE <var> NO_POLICY_SCOPE)')
	
	def testIfExists(self):
		cm = CMakeInterpreter()
		cm.interpret("""
			if(NOT EXISTS """+'"'+str(thisFile)+'"'+""")
				set(exists "ON")
			else()
				set(exists "OFF")
			endif()
		""")
		self.assertEqual(cm.ns["exists"], "OFF")

if __name__ == '__main__':
	unittest.main()
