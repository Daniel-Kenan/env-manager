import os
import shutil
import json
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from getpass import getpass
from colorama import Fore, Style
import base64
import secrets

# Ensure colorama works correctly on Windows
import colorama
colorama.init()

PROJECTS_FILE = 'projects.json'
PROJECTS_DIR = 'projects'
SALT_LENGTH = 16

# Supported .env file extensions
ENV_EXTENSIONS = ['.env', '.env.local', '.env.development', '.env.production']

def load_projects():
    """Load projects from the JSON file."""
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_projects(projects):
    """Save projects to the JSON file."""
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=4)

def ensure_projects_directory():
    """Create a projects directory if it doesn't exist."""
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)

def list_projects(projects):
    """List all available projects."""
    return [name for name in projects.keys()]

def create_project(project_name, project_path, projects):
    """Create a new project directory and copy all .env files."""
    if project_name in projects:
        print(f"{Fore.RED}Project '{project_name}' already exists.{Style.RESET_ALL}")
        return

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)

    print(f"{Fore.CYAN}Copying .env files from '{project_path}'...{Style.RESET_ALL}")
    
    files_copied = False

    for ext in ENV_EXTENSIONS:
        env_file_path = os.path.join(project_path, ext)
        if os.path.exists(env_file_path):
            shutil.copy(env_file_path, project_dir)
            print(f"{Fore.GREEN}Copied '{ext}' to project '{project_name}'.{Style.RESET_ALL}")
            files_copied = True
    
    if not files_copied:
        print(f"{Fore.RED}No .env file found at '{project_path}' with supported extensions: {', '.join(ENV_EXTENSIONS)}.{Style.RESET_ALL}")
        return
    
    # Encrypt files if user chooses to do so
    encrypt_choice = input(f"{Fore.YELLOW}Do you want to encrypt the copied files? (Y/n) [{Fore.GREEN}Y{Fore.YELLOW}]: {Style.RESET_ALL}").strip().lower() or 'y'
    if encrypt_choice == 'y':
        # Prompt for password
        password = getpass(f"{Fore.YELLOW}Enter a password to encrypt the copied files: {Style.RESET_ALL}")
        confirm_password = getpass(f"{Fore.YELLOW}Confirm the password: {Style.RESET_ALL}")

        if password != confirm_password:
            print(f"{Fore.RED}Passwords do not match. Aborting encryption.{Style.RESET_ALL}")
            return

        for ext in ENV_EXTENSIONS:
            copied_file_path = os.path.join(project_dir, ext)
            if os.path.exists(copied_file_path):
                encrypt_file(copied_file_path, password)
        
        # Prompt for deletion of unencrypted files
        delete_choice = input(f"{Fore.YELLOW}Do you want to delete the unencrypted files? (Y/n) [{Fore.GREEN}Y{Fore.YELLOW}]: {Style.RESET_ALL}").strip().lower() or 'y'
        if delete_choice == 'y':
            for ext in ENV_EXTENSIONS:
                copied_file_path = os.path.join(project_dir, ext)
                if os.path.exists(copied_file_path):
                    os.remove(copied_file_path)
                    print(f"{Fore.GREEN}Deleted unencrypted file '{copied_file_path}'.{Style.RESET_ALL}")

    projects[project_name] = project_path
    save_projects(projects)

def encrypt_file(file_path, password):
    """Encrypt a file using a provided password."""
    salt = secrets.token_bytes(SALT_LENGTH)
    key = derive_key(password, salt)
    fernet = Fernet(key)

    with open(file_path, 'rb') as file:
        original = file.read()

    encrypted = fernet.encrypt(original)

    encrypted_file_path = file_path + '.encrypted'
    with open(encrypted_file_path, 'wb') as encrypted_file:
        encrypted_file.write(salt + encrypted)  # Prepend salt to the encrypted data

    print(f"{Fore.GREEN}File '{file_path}' encrypted successfully as '{encrypted_file_path}'.{Style.RESET_ALL}")

def derive_key(password, salt):
    """Derive a key from a password and salt using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def decrypt_file(file_path, password):
    """Decrypt an encrypted file using a provided password."""
    with open(file_path, 'rb') as file:
        data = file.read()
    
    salt = data[:SALT_LENGTH]
    encrypted = data[SALT_LENGTH:]

    key = derive_key(password, salt)
    fernet = Fernet(key)

    try:
        decrypted = fernet.decrypt(encrypted)
    except Exception as e:
        print(f"{Fore.RED}Decryption failed: {e}{Style.RESET_ALL}")
        return

    decrypted_file_path = file_path.replace('.encrypted', '')
    with open(decrypted_file_path, 'wb') as decrypted_file:
        decrypted_file.write(decrypted)

    print(f"{Fore.GREEN}File '{file_path}' decrypted successfully as '{decrypted_file_path}'.{Style.RESET_ALL}")

def display_menu():
    """Display the main menu."""
    print(f"\n{Fore.CYAN}--- .env Manager ---{Style.RESET_ALL}")
    print("1. Create a new project and copy .env")
    print("2. Decrypt an encrypted .env file")
    print("3. Exit")

def main():
    ensure_projects_directory()
    projects = load_projects()

    while True:
        display_menu()

        choice = input(f"{Fore.YELLOW}Choose an option (1-3): {Style.RESET_ALL}")
        
        if choice == '1':
            project_name = input(f"{Fore.YELLOW}Enter new project name: {Style.RESET_ALL}")
            project_path = input(f"{Fore.YELLOW}Enter the full path of the project (where the .env files are located): {Style.RESET_ALL}")
            create_project(project_name, project_path, projects)
        
        elif choice == '2':
            file_to_decrypt = input(f"{Fore.YELLOW}Enter the path of the encrypted .env file to decrypt: {Style.RESET_ALL}")
            if os.path.exists(file_to_decrypt):
                password = getpass(f"{Fore.YELLOW}Enter the password to decrypt the file: {Style.RESET_ALL}")
                decrypt_file(file_to_decrypt, password)
            else:
                print(f"{Fore.RED}File not found: {file_to_decrypt}{Style.RESET_ALL}")
        
        elif choice == '3':
            print(f"{Fore.CYAN}Exiting...{Style.RESET_ALL}")
            break
        
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
