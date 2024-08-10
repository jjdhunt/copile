class BlackListedModuleImportError(Exception):
    def __init__(self, source, used_blacklisted_modules):
        self.message = f"""
The copiled source code used the blacklisted module(s): {used_blacklisted_modules}.
If you are sure you want to allow use of this blacklisted module in (only) this function\'s copilation, add it to the copile decorator's module whitelist like this: @copile(module_whitelist={used_blacklisted_modules})
You should review the copiled source before whitelisting. The copiled source was:\n{source}
"""
        super().__init__(self.message)

class BlackListedFunctionUseError(Exception):
    def __init__(self, source, used_blacklisted_functions):
        self.message = f"""
The copiled source code used the blacklisted function(s): {used_blacklisted_functions}.'
If you are sure you want to allow use of this blacklisted function in (only) this function\'s copilation, add it to the copile decorator's function whitelist like this: @copile(function_whitelist={used_blacklisted_functions})
You should review the copiled source before whitelisting. The copiled source was:\n{source}
"""
        super().__init__(self.message)

class CopiledSourceDeemedUnsafeError(Exception):
    def __init__(self, source, issues):
        self.message = f"""
AI has deemed the copiled source code to be unsafe because it had the issues: {issues}.
If you are sure you want to allow this unsafe behavior in (only) this function\'s copilation, add it to the copile decorator's unsafe overrides like this: @copile(unsafe_overrides={issues})
You should review the copiled source before whitelisting. The copiled source was:\n{source}
"""
        super().__init__(self.message)

class CopiledSourceCodeNeedsModule(Exception):
    def __init__(self, module_name):
        self.message = f'The copiled code wanted to use the module "{module_name}" but it is not installed. Try `pip install {module_name}`.'
        super().__init__(self.message)

class SpecificationUnclearError(Exception):
    def __init__(self, callable_name, description):
        self.message = f'The specification for "{callable_name}()" is unclear. The AI says:\n"{description}".'
        super().__init__(self.message)