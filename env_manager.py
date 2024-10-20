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
from InquirerPy import inquirer  # Import InquirerPy for interactive prompts

# Ensure colorama works correctly on Windows
import colorama
colorama.init()

PROJECTS_DIR = 'projects'
SALT_LENGTH = 16

# Supported .env file extensions
ENV_EXTENSIONS = ['.env', '.env.local', '.env.development', '.env.production']

def ensure_projects_directory():
    """Create a projects directory if it doesn't exist."""
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)

def list_projects():
    """List all available projects from the filesystem."""
    return [name for name in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, name))]

def create_project(project_name, project_path):
    """Create a new project directory and copy all .env files."""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if os.path.exists(project_dir):
        print(f"{Fore.YELLOW}Warning: Project '{project_name}' already exists. Overwriting it may lead to loss of data.{Style.RESET_ALL}")
        overwrite_choice = input(f"{Fore.YELLOW}Do you want to continue? (Y/n) [{Fore.GREEN}Y{Fore.YELLOW}]: {Style.RESET_ALL}").strip().lower() or 'y'
        if overwrite_choice != 'y':
            print(f"{Fore.RED}Aborted project creation.{Style.RESET_ALL}")
            return

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
        # Clean up the created directory and exit
        shutil.rmtree(project_dir)
        return

    # Encrypt files if user chooses to do so
    encrypt_choice = input(f"{Fore.YELLOW}Do you want to encrypt the copied files? (Y/n) [{Fore.GREEN}Y{Fore.YELLOW}]: {Style.RESET_ALL}").strip().lower() or 'y'
    if encrypt_choice == 'y':
        # Prompt for password
        password = getpass(f"{Fore.YELLOW}Enter a password to encrypt the copied files: {Style.RESET_ALL}")
        confirm_password = getpass(f"{Fore.YELLOW}Confirm the password: {Style.RESET_ALL}")

        if password != confirm_password:
            print(f"{Fore.RED}Passwords do not match. Aborting encryption and cleaning up.{Style.RESET_ALL}")
            shutil.rmtree(project_dir)  # Clean up on password mismatch
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

def delete_project(project_name):
    """Delete a project and its directory."""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        print(f"{Fore.GREEN}Deleted project '{project_name}' and its directory.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Project '{project_name}' does not exist.{Style.RESET_ALL}")

def view_encrypted_files(project_name):
    """Display all encrypted .env files for the selected project."""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    encrypted_files = [f for f in os.listdir(project_dir) if f.endswith('.encrypted')]
    
    if encrypted_files:
        print(f"{Fore.CYAN}Encrypted files for project '{project_name}':{Style.RESET_ALL}")
        for file in encrypted_files:
            print(f" - {file}")
    else:
        print(f"{Fore.RED}No encrypted files found for project '{project_name}'.{Style.RESET_ALL}")

def display_menu():
    """Display the main menu."""
    options = [
        "Create a new project and copy .env",
        "Decrypt an encrypted .env file",
        "View encrypted files in a project",
        "Delete a project",
        "Exit"
    ]
    choice = inquirer.select(
        message="--- .env Manager ---",
        choices=options
    ).execute()
    return choice

def choose_project():
    """Allow the user to choose a project from a list using arrow keys."""
    project_list = list_projects()
    if not project_list:
        print(f"{Fore.RED}No projects available.{Style.RESET_ALL}")
        return None
    
    project_name = inquirer.select(
        message="Choose a project:",
        choices=project_list
    ).execute()
    
    return project_name

def main():
    ensure_projects_directory()

    while True:
        choice = display_menu()

        if choice == "Create a new project and copy .env":
            project_name = input(f"{Fore.YELLOW}Enter new project name: {Style.RESET_ALL}")
            project_path = input(f"{Fore.YELLOW}Enter the full path of the project (where the .env files are located): {Style.RESET_ALL}")
            create_project(project_name, project_path)

        elif choice == "Decrypt an encrypted .env file":
            project_name = choose_project()
            if project_name:
                encrypted_files_found = False
                for ext in ENV_EXTENSIONS:
                    file_to_decrypt = os.path.join(PROJECTS_DIR, project_name, ext + '.encrypted')
                    if os.path.exists(file_to_decrypt):
                        encrypted_files_found = True
                        break

                if not encrypted_files_found:
                    print(f"{Fore.RED}No encrypted files found in project '{project_name}'.{Style.RESET_ALL}")
                    continue

                password = getpass(f"{Fore.YELLOW}Enter the password to decrypt: {Style.RESET_ALL}")
                for ext in ENV_EXTENSIONS:
                    file_to_decrypt = os.path.join(PROJECTS_DIR, project_name, ext + '.encrypted')
                    if os.path.exists(file_to_decrypt):
                        decrypt_file(file_to_decrypt, password)

        elif choice == "View encrypted files in a project":
            project_name = choose_project()
            if project_name:
                view_encrypted_files(project_name)

        elif choice == "Delete a project":
            project_name = choose_project()
            if project_name:
                delete_project(project_name)

        elif choice == "Exit":
            print(f"{Fore.CYAN}Exiting...{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    main()
