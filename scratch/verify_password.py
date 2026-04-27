import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

try:
    from auth.service import validate_password
    
    # Test cases
    test_passwords = [
        ("short1", "A senha deve ter pelo menos 8 caracteres."),
        ("lowercase1", None), # Should be OK now
        ("UPPERCASE1", None), # Should be OK
        ("no_number", "A senha deve conter pelo menos um número."),
    ]
    
    for pwd, expected in test_passwords:
        result = validate_password(pwd)
        print(f"Testing '{pwd}': Expected '{expected}', Got '{result}'")
        if result != expected:
            print("FAILURE!")
            sys.exit(1)
            
    print("SUCCESS: All password validation tests passed!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
