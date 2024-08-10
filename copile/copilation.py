import os
from dotenv import load_dotenv, set_key
from openai import OpenAI
from typing import List, Optional, Union
import inspect
import sys
import importlib.util
import ast
import subprocess
import hashlib

from . import copilation_errors as errors
from . import system_messages as sm

def _save_api_key(api_key: str):
    """
    Save an OPENAI_API_KEY key in a dotenv file.

    Given an API key, save it under the key 'OPENAI_API_KEY' in a python dotenv file named '.env' at the root of the current project.
    If the file does not exist, it creates it. If the 'OPENAI_API_KEY' key already exists, it overwrites it.

    Args:
        api_key (str): The API key to be saved.

    """
    dotenv_path = '.env'
    load_dotenv(dotenv_path)
    set_key(dotenv_path, "OPENAI_API_KEY", api_key)


def _get_completion(comment:str, system_message:str, model_class:str='fast', temperature:float=0):
    load_dotenv()

    client = OpenAI()

    models = {'fast': 'gpt-4o-mini',
              'best': 'gpt-4o'}
    
    model_max_tokens = {'gpt-4o-mini': 128000,
                        'gpt-4o': 128000,
                        'gpt-3.5-turbo-1106': 16000,
                        'gpt-4-1106-preview': 128000
                       }

    model = models[model_class]

    max_characters = int(model_max_tokens[model] * 0.9 * 4) #90% of max to allow for some deviation from the nominal 4 characters/token 
    if len(comment) > max_characters:
        completion = f'Could not get a completion because the number of characters ({len(comment)}) exceeds the max allowed ({max_characters}).'
    else:
        completion = client.chat.completions.create(
                                                    model=model,
                                                    temperature=temperature,
                                                    messages=[
                                                        {"role": "system", "content": system_message},
                                                        {"role": "user", "content": comment}
                                                    ],
                                                    )
    return completion.choices[0].message.content


def _strip_special(s:str, prefixes:Optional[List[str]]=[], suffixes:Optional[List[str]]=[]) -> str:
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]
    for suffix in suffixes:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    return s


def _clean_response(response):
    # Clean up the response. Gpt can add unwanted decorators and things.
    prefixes = ["'", "```python", "```json"]
    suffixes = ["'", "```"]
    return _strip_special(response, prefixes, suffixes).strip()


def _parse_callable_name(source_code):
    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
            return node.name
    return None

def _get_existing_copilation(copilation_filename:str, callable_name:str):
    spec = importlib.util.spec_from_file_location('test_module_name', copilation_filename)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except FileNotFoundError:
        return None
    try:
        return getattr(module, callable_name)
    except AttributeError:
        return None


def _move_imports_to_top(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    imports = []
    others = []

    for line in lines:
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            imports.append(line.strip() + '\n')
        else:
            others.append(line)

    with open(file_path, 'w') as f:
        f.writelines(imports)
        f.writelines(others)


def _rewrite_copiled_source(copilation_filename:str, callable_name:str, new_source_code):
    """
    Overwrite the original copiled source code with the new source code.
    """
    spec = importlib.util.spec_from_file_location("copile", copilation_filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source_code = inspect.getsource(getattr(module, callable_name))
    with open(copilation_filename, "r+") as file:
        lines = file.readlines()
        function_start_line = inspect.getsourcelines(getattr(module, callable_name))[1]
        function_end_line = function_start_line + len(source_code.split('\n'))
        lines[function_start_line - 1:function_end_line] = new_source_code + '\n\n\n'
        file.seek(0)
        file.writelines(lines)
        file.truncate()        


def _write_copiled_source(copilation_filename:str, callable_name:str, source_code:str):
    """
    Write the copiled source code to file.
    """
    if _get_existing_copilation(copilation_filename, callable_name):
        _rewrite_copiled_source(copilation_filename, callable_name, source_code)
    else:
        with open(copilation_filename, 'a+') as file:
            file.write(f"\n\n{source_code}")

    # move imports to top of file
    _move_imports_to_top(copilation_filename)
    subprocess.run(["isort", "--quiet", copilation_filename])
    subprocess.run(["black", "--quiet", copilation_filename])


def _get_calling_filename(func):
    path = inspect.getfile(func)
    return os.path.basename(path)


def _source_to_object(source:str):
    source_name = _parse_callable_name(source)
    globals_dict = {}
    exec(source, globals_dict)
    return globals_dict[source_name]


def load_list(filename: str) -> list[str]:
    """
    Loads a newline-separated list of strings from a file and returns them as a list of strings.

    Args:
        filename (str): The path to the file containing the newline-separated list of strings.

    Returns:
        list[str]: A list of strings read from the file.
    """
    with open(filename, 'r') as file:
        return file.read().splitlines()


def check_for_blacklisted_modules_used(source_code: str, blacklist: List[str]) -> Optional[List[str]]:
    """
    Checks if the source code uses any of the blacklisted modules.

    Args:
        source_code (str): The source code to check.
        blacklist (List[str]): A list of module names that are blacklisted.

    Returns:
        Optional[List[str]]: A list of all blacklisted modules used, or None if none are used.
    """
    used_modules = []
    for module in blacklist:
        if f"import {module}" in source_code or f"from {module} import" in source_code:
            used_modules.append(module)
    return used_modules

def check_for_blacklisted_functions_used(source: str, blacklisted_functions: List[str]) -> List[str]:
    """
    Checks the source code for any usage of blacklisted functions and returns their names.

    Args:
        source: A string containing the source code to be checked.
        blacklisted_functions: A set of strings representing the names of functions that are blacklisted.

    Returns:
        A list of strings representing the names of blacklisted functions that are used in the source code.
    """

    # Helper function to recursively find function calls
    def find_function_calls(node, found):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in blacklisted_functions:
                    found.add(child.func.id)
            find_function_calls(child, found)

    # Parse the source code into an AST
    tree = ast.parse(source)
    found_blacklisted_functions = set()
    find_function_calls(tree, found_blacklisted_functions)

    return list(found_blacklisted_functions)

def _review_safety(source:str, module_whitelist=[], function_whitelist=[], unsafe_overrides=[]):

    # check for imports of blacklisted modules
    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, 'module_blacklist.txt')
    module_blacklist = list(set(load_list(file_path)) - set(module_whitelist))
    used_blacklisted_modules = check_for_blacklisted_modules_used(source, module_blacklist)
    if used_blacklisted_modules:
        raise errors.BlackListedModuleImportError(source, used_blacklisted_modules)
    
    # check for use of blacklisted functions
    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, 'function_blacklist.txt')
    function_blacklist = list(set(load_list(file_path)) - set(function_whitelist))
    used_blacklisted_functions = check_for_blacklisted_functions_used(source, function_blacklist)
    if used_blacklisted_functions:
        raise errors.BlackListedFunctionUseError(source, used_blacklisted_functions)
    
    # have gpt review source code for unsafe activites  
    issues = _get_completion(source, sm.check_for_safety_issues, model_class='best')
    issues = set(issues.split(', '))
    issues = issues - set(unsafe_overrides)
    issues = issues - {'NONE'}
    if issues:
        raise errors.CopiledSourceDeemedUnsafeError(source, issues)

def _review_specification(callable_name:str, specification:str):
    issues = _get_completion(specification, sm.assess_specification, model_class='fast')
    if issues.startswith('UNCLEAR'):
        raise errors.SpecificationUnclearError(callable_name, issues)

def _copiler(func, force_copilation=False, module_whitelist:Union[str,List[str]]=[], function_whitelist:Union[str,List[str]]=[], unsafe_overrides:Union[str,List[str]]=[]):
        if not isinstance(module_whitelist, list):
            module_whitelist = [module_whitelist]

        if not isinstance(function_whitelist, list):
            function_whitelist = [function_whitelist]

        if not isinstance(unsafe_overrides, list):
            unsafe_overrides = [unsafe_overrides]
        
        specification = inspect.getsource(func)
        specification = '\n'.join(specification.splitlines()[1:])
        callable_name = _parse_callable_name(specification)
        calling_filename = _get_calling_filename(func)
        copilations_filename = f"co_{calling_filename.split('.')[0]}.py"
        copilations_filename = f"{callable_name}.co.py"
        copilations_filename = './copilations/' + copilations_filename

        if not os.path.isdir('copilations'):
            os.makedirs('copilations', exist_ok=True)

        existing_copilation = _get_existing_copilation(copilations_filename, callable_name)

        if force_copilation or not existing_copilation:

            _review_specification(callable_name, specification)

            max_tries = 2
            tries = 0
            stop_trying = False
            model_class = 'best'
            while tries < max_tries and not stop_trying:
                copiled_source = f'def {callable_name}(me):\n    return me\n'
                copiled_source = _get_completion(specification, sm.copile_from_specification, model_class=model_class)
                copiled_source = _clean_response(copiled_source)

                # if copiled_source.startswith('ERROR'):
                #     raise errors.SpecificationUnclearError(callable_name, copiled_source.removeprefix('ERROR: '))
                
                _review_safety(copiled_source,
                               module_whitelist=module_whitelist,
                               function_whitelist=function_whitelist,
                               unsafe_overrides=unsafe_overrides) # will assert if source is deemed unsafe
                try:
                    func = _source_to_object(copiled_source)
                    _write_copiled_source(copilations_filename, callable_name, copiled_source)
                    print(f"The specification for '{callable_name}()' was copiled in {copilations_filename}")
                    return func
                except ModuleNotFoundError as e:
                    raise errors.CopiledSourceCodeNeedsModule(e.name) from None
                except:
                    tries += 1
                    model_class = 'best'

            print(f"The source returned from {model_class} was bad! The source returned was:\n")
            print(copiled_source)
            return None
        
        else:
            return existing_copilation

def copile(*args, force_copilation=False, module_whitelist:Union[str,List[str]]=[], function_whitelist:Union[str,List[str]]=[], unsafe_overrides:Union[str,List[str]]=[]):
    if len(args) == 1 and callable(args[0]):
        # Decorator used without arguments
        func = args[0]
        return _copiler(func)
    
    else:
        return lambda func: _copiler(func,
                                    force_copilation=force_copilation,
                                    module_whitelist=module_whitelist,
                                    function_whitelist=function_whitelist,
                                    unsafe_overrides=unsafe_overrides,
                                    )

def save_hash_to_file(string: str, filename: str) -> None:
    """Hashes a given string and saves the hash to a specified file.

    Args:
        string (str): The string to be hashed.
        filename (str): The name of the file where the hash will be saved.
    """
    
    def hash_string(s: str) -> str:
        """Generates a SHA-256 hash of the input string.

        Args:
            s (str): The string to hash.

        Returns:
            str: The hexadecimal representation of the hash.
        """
        return hashlib.sha256(s.encode()).hexdigest()

    hash_value = hash_string(string)
    
    with open(filename, 'w') as file:
        file.write(hash_value)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python copile.py <OPENAI_API_KEY>")
    else:
        parameter = sys.argv[1]
        _save_api_key(parameter)