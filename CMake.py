import typing
from pathlib import Path
import json
import re
from collections import OrderedDict

import cmakeast
import os


cmakeConstants = {
	"ON": True,
	"YES": True,
	"TRUE": True,
	"Y": True,
	
	"OFF": False,
	"NO": False,
	"FALSE": False,
	"N": False,
}

class Arg:
	__slots__ = ("type", "optional", "nameMandatory")
	def __init__(self, typ:type, optional:bool=False, nameMandatory:bool=False):
		self.type = typ
		self.optional = optional
		self.nameMandatory = nameMandatory

def parseFuncArgs(interp, spec: typing.Mapping[str, Arg], args:typing.Iterable):
	#print("parseFuncArgs", args)
	res = OrderedDict()
	specIter = iter(spec)
	
	j = 0
	for argName, argCand in specIter:
		arg = args[j]
		#print(argName, j, arg)
		wasSet = False
		if not argCand.optional:
			if argCand.nameMandatory:
				assert isinstance(arg, cmakeast.ast.Word) and arg.type == cmakeast.ast.WordType.Variable and arg.contents == argName
				j += 1
			res[argName] = interp.evaluateExpression(arg)
		else:
			if argCand.nameMandatory:
				if isinstance(arg, cmakeast.ast.Word) and arg.type == cmakeast.ast.WordType.Variable:
					if arg.contents == argName:
						if argCand.type is bool:
							res[argName] = True
							wasSet = True
						else:
							j += 1
							arg = args[j]
							res[argName] = interp.evaluateExpression(arg)
							wasSet = True

				if not wasSet:
					if argCand.type is bool:
						res[argName] = False
					else:
						res[argName] = None
		j += 1
		if j >= len(args):
			break
	
	for argName, argCand in specIter:
		res[argName] = False if argCand.type is bool else None
	
	return res

includeSpec = [
	("path", Arg(str, False, False)),
	("OPTIONAL", Arg(bool, True, True)),
	("RESULT_VARIABLE", Arg(str, True, True)),
	("NO_POLICY_SCOPE", Arg(bool, True, True)),
]

messageSpec = [
	("mode", Arg(str, False, False)),
	("text", Arg(str, False, False)),
]

setSpec = [
	("variable", Arg(str, False, False)),
	("value", Arg(str, False, False)),
	
	#following vars are for CACHE
	#("CACHE", Arg(bool, False, False)),
	#<type> {"BOOL", "FILEPATH", "PATH", "STRING", "INTERNAL"}
	#("docstring", Arg(str, False, False)),
	#("FORCE", Arg(bool, True, False)),
	
	#("PARENT_SCOPE", Arg(bool, False, False)),
]

class cmakeBuiltins():
	@classmethod
	def set(cls, interp, args):
		argsRes = []
		for a in args[1:]:
			argsRes.append(interp.evaluateExpression(a))
		
		name=interp.evaluateExpression(args[0])
		namespace = interp.ns
		if name.startswith("ENV{") and name[-1] == "}":
			name = name[4:-1]
			namespace = interp.envVars
		
		if len(argsRes) >= 2:
			namespace[name] = argsRes
		else:
			namespace[name] = argsRes[0]
	
	@classmethod
	def message(cls, interp, args):
		argz = parseFuncArgs(interp, messageSpec, args)
		#print(argz)
		if argz["mode"] in {"FATAL_ERROR", }:
			raise Exception("Fatal error in message: " + argz["text"])
		elif argz["mode"] in {"WARNING", "AUTHOR_WARNING", "DEPRECATION", "SEND_ERROR"}:
			import warnings
			warnings.warn(argz["mode"]+": "+ argz["text"])
		else:
			print(argz["text"])
	
	@classmethod
	def include(cls, interp, args):
		argz = parseFuncArgs(interp, includeSpec, args)
		modulePath = Path(argz["path"])
		if not modulePath.is_file():
			if "CMAKE_MODULE_PATH" in interp.ns:
				modulePath= Path(interp.ns["CMAKE_MODULE_PATH"]) / (argz["path"]+".cmake")
		
		try:
			interp.interpret(modulePath.read_text())
			if argz["RESULT_VARIABLE"]:
				interp.ns[argz["RESULT_VARIABLE"]] = str(modulePath)
		except:
			if argz["RESULT_VARIABLE"]:
				interp.ns[argz["RESULT_VARIABLE"]] = argz["RESULT_VARIABLE"]+"-NOTFOUND"
			
			if not argz["OPTIONAL"]:
				raise


stringEmbeddedExprRx = re.compile("\\$\\{[^\\}\\{\\$\\n]+\\}")

class CMakeInterpreter():
	__slots__ = ("ns", "cache", "builtins", "envVars")
	def __init__(self, ns=None, cache=None, builtins=None, envVars=None):
		if ns is None:
			ns = {}
		if cache is None:
			cache = {}
		if envVars is None:
			envVars = OrderedDict(os.environ)
		
		if builtins is None:
			builtins = cmakeBuiltins

		self.ns = ns
		self.cache = cache
		self.builtins = builtins
		self.envVars = envVars
	
	def evaluateConditions(self, conditions):
		conditionsInitial = conditions
		if isinstance(conditions, cmakeast.ast.Word):
			return [self.evaluateCondition(conditions)]
		
		if isinstance(conditions, (list, tuple)):
			if not conditions:
				return []
			if(len(conditions) == 1):
				res = self.evaluateConditions(conditions[0])
				#print("result conditions", res)
				return res
			
			#print("conditions non unary", conditions)
			if conditions[0].type == cmakeast.ast.TokenType.Word:
				invertCondition = False
				if(conditions[0].contents == "NOT"):
					#print("invertCondition = True")
					invertCondition = True
					conditions = conditions[1:]
				else:
					#print("invertCondition = False")
					pass
				
				if(conditions[0].contents == "EXISTS"):
					res = Path(self.evaluateExpression(conditions[1])).exists()
					conditions = [(not res if invertCondition else res), *self.evaluateConditions(conditions[2:])]
					#print(conditionsInitial, "->", conditions)
					return conditions
				elif(conditions[0].contents == "IS_DIRECTORY"):
					res = Path(self.evaluateExpression(conditions[1])).is_dir()
					conditions = [(not res if invertCondition else res), *self.evaluateConditions(conditions[2:])]
					#print(conditionsInitial, "->", conditions)
					return conditions
				
				elif invertCondition:
					exprToInverseResult = self.evaluateCondition(conditions[0])
					#print(conditions[0], "->", exprToInverseResult)
					conditions = [not exprToInverseResult, *self.evaluateConditions(conditions[1:])]
					#print(conditionsInitial, "->", conditions)
					return conditions
			
			if conditions[1].type == cmakeast.ast.TokenType.Word:
				if(conditions[1].contents == "AND"):
					conditions = [self.evaluateCondition(conditions[0]) and self.evaluateConditions(conditions[2]), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "OR"):
					conditions = [self.evaluateCondition(conditions[0]) or self.evaluateConditions(conditions[2:])]
				elif(conditions[1].contents == "LESS" or conditions[1].contents == "STRLESS"):
					conditions = [self.evaluateExpression(conditions[0]) < self.evaluateExpression(conditions[2]), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "GREATER" or conditions[1].contents == "STRGREATER"):
					conditions = [self.evaluateExpression(conditions[0]) > self.evaluateExpression(conditions[2]), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "LESS_EQUAL" or conditions[1].contents == "STRLESS_EQUAL"):
					conditions = [self.evaluateExpression(conditions[0]) <= self.evaluateExpression(conditions[2]), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "GREATER_EQUAL" or conditions[1].contents == "STRGREATER_EQUAL"):
					conditions = [self.evaluateExpression(conditions[0]) >= self.evaluateExpression(conditions[2]), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "EQUAL" or conditions[1].contents == "STREQUAL"):
					conditions = [self.evaluateExpression(conditions[0]) == self.evaluateExpression(conditions[2]), *self.evaluateConditions(conditions[3:])]

				elif(conditions[1].contents == "VERSION_LESS"):
					conditions = [self.evaluateExpression(conditions[0]).split(".") < self.evaluateExpression(conditions[2]).split("."), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "VERSION_GREATER"):
					conditions = [self.evaluateExpression(conditions[0]).split(".") > self.evaluateExpression(conditions[2]).split("."), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "VERSION_LESS_EQUAL" or conditions[1].contents == "STRLESS_EQUAL"):
					conditions = [self.evaluateExpression(conditions[0]).split(".") <= self.evaluateExpression(conditions[2]).split("."), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "VERSION_EQUAL" or conditions[1].contents == "STRLESS_EQUAL"):
					conditions = [self.evaluateExpression(conditions[0]).split(".") == self.evaluateExpression(conditions[2]).split("."), *self.evaluateConditions(conditions[3:])]
				elif(conditions[1].contents == "MATCHES"):
					rx = self.evaluateExpression(conditions[2:])
					rx = re.compile(re)
					conditions = [bool(rx.match(self.evaluateExpression(conditions[0]))), *self.evaluateConditions(conditions[3:])]
		else:
			pass
		#print("result conditions", conditions)
		return conditions
	
	def evaluateCondition(self, condition):
		#print("condition", condition)
		if condition.type == cmakeast.ast.TokenType.Word or condition.type == cmakeast.ast.WordType.Variable:
			try:
				exprRes = self.evaluateExpression(condition)
				#print("exprRes", exprRes)
			except Exception as ex:
				print(ex)
				return None
			
			if isinstance(exprRes, str):
				if exprRes in self.ns:
					return self.ns[exprRes]
				else:
					return False
			else:
				return exprRes
		
		raise NotImplementedError()
	
	def derefVariable(self, expr:str):
		assert expr[0:2] == "${"
		assert expr[-1] == "}"
		exprName = expr[2:-1]
		#print("exprName", exprName, exprName in self.ns)
		if exprName in self.ns:
			return self.ns[exprName]
		else:
			return ""
	
	def evalStringEmbeddedExpr(self, m):
		#print(evalEmbExpr, m.group(0))
		res = self.derefVariable(m.group(0))
		#print("res", res)
		return res
	
	
	def evaluateExpression(self, expr):
		#print("unary expression", expr)
		#assert conditions.type == cmakeast.ast.TokenType.Word or conditions.type == cmakeast.ast.TokenType.Variable
		if expr.type == cmakeast.ast.TokenType.Word or expr.type == cmakeast.ast.WordType.CompoundLiteral:
			if expr.contents in cmakeConstants:
				#print("result expr", cmakeConstants[expr.contents])
				return cmakeConstants[expr.contents]
			try:
				num = int(expr.contents)
				#print("number", num)
				return num
			except:
				pass
			return expr.contents
		elif expr.type == cmakeast.ast.WordType.String:
			res = json.loads(expr.contents)
			count = 1
			while count:
				res, count = stringEmbeddedExprRx.subn(self.evalStringEmbeddedExpr, res)
			return res
		elif expr.type == cmakeast.ast.WordType.VariableDereference:
			return self.derefVariable(expr.contents)
		
		#print("result expr", False)
		raise ValueError("Neither a Word nor a deref: "+repr(expr))

	def _interpret(self, statements):
		for s in statements:
			if isinstance(s, cmakeast.ast.FunctionCall):
				fName = s.name.lower()
				#print("hasattr(self.builtins ("+repr(self.builtins)+"), "+repr(s.name)+")", hasattr(self.builtins, fName))
				if hasattr(self.builtins, fName):
					func = getattr(self.builtins, fName)
					func(self, s.arguments)
				else:
					raise ValueError("Function "+repr(s.name)+" not found")
				continue
			elif isinstance(s, cmakeast.ast.IfBlock):
				cond = s.if_statement.header.arguments
				trueBranch=s.if_statement.body if s.if_statement else None
				elseif_statements=s.elseif_statements
				falseBranch=s.else_statement.body if s.else_statement else None
				
				evaluatedCond = self.evaluateConditions(cond)
				#print("evaluatedCond", evaluatedCond)
				assert len(evaluatedCond) == 1
				evaluatedCond = evaluatedCond[0]
				if evaluatedCond and trueBranch:
					self._interpret(trueBranch)
				#TODO: elseif_statements
				elif falseBranch:
					self._interpret(falseBranch)
				continue
			#print("s", s)
	
	def interpret(self, source:typing.Union[str, Path]):
		if isinstance(source, Path):
			return self.interpret(source.read_text())
		
		a = cmakeast.ast.parse(source)
		self._interpret(a.statements)
		
		return self.ns

def __main__():
	import sys
	cm = CMakeInterpreter()
	cm.interpret(Path(sys.argv[1]))
	from pprint import pprint
	pprint(cm.ns)

if __name__ == "__main__":
	__main__()
