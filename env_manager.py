import os
import shutil
import zipfile
import tarfile
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

def compress_projects():
    """Compress the projects directory into a specified format."""
    compression_choice = inquirer.select(
        message="Choose a compression format:",
        choices=["ZIP", "TAR"],
    ).execute()

    misleading_extension = inquirer.text(
        message="Enter a misleading file extension (e.g., .txt, .docx):",
        default=".hidden"
    ).execute()

    compressed_filename = os.path.join(os.getcwd(), f"projects.{misleading_extension}")

    print(f"{Fore.YELLOW}This tool will compress the projects folder. Make sure to upload the compressed file to the cloud.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}The compressed file is safe to store and share.{Style.RESET_ALL}")

    if compression_choice == "ZIP":
        with zipfile.ZipFile(compressed_filename, 'w') as zipf:
            for root, _, files in os.walk(PROJECTS_DIR):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), PROJECTS_DIR))
        print(f"{Fore.GREEN}Projects folder compressed successfully to '{compressed_filename}'.{Style.RESET_ALL}")

    elif compression_choice == "TAR":
        with tarfile.open(compressed_filename, 'w:gz') as tarf:
            tarf.add(PROJECTS_DIR, arcname=os.path.basename(PROJECTS_DIR))
        print(f"{Fore.GREEN}Projects folder compressed successfully to '{compressed_filename}'.{Style.RESET_ALL}")

def import_projects():
    """Import projects from a compressed file with retry logic for misleading extensions."""
    compressed_file_path = inquirer.text(message="Enter the path of the compressed file to import:").execute()

    if not os.path.exists(compressed_file_path):
        print(f"{Fore.RED}The specified file does not exist.{Style.RESET_ALL}")
        return

    # Try to extract directly first
    def try_extract(path, ext):
        try:
            if ext == '.zip':
                with zipfile.ZipFile(path, 'r') as zipf:
                    # Extract to a temp directory first
                    temp_dir = os.path.join(PROJECTS_DIR, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    zipf.extractall(temp_dir)
                    
                    # Move files from the temp directory to PROJECTS_DIR, avoiding nested folders
                    for item in os.listdir(temp_dir):
                        source = os.path.join(temp_dir, item)
                        destination = os.path.join(PROJECTS_DIR, item)
                        shutil.move(source, destination)

                    # Cleanup the temp directory
                    shutil.rmtree(temp_dir)
                    
                print(f"{Fore.GREEN}Projects imported successfully from '{path}' as ZIP.{Style.RESET_ALL}")
                return True
            
            elif ext == '.tar.gz' or ext == '.tgz':
                with tarfile.open(path, 'r:gz') as tarf:
                    temp_dir = os.path.join(PROJECTS_DIR, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    tarf.extractall(temp_dir)

                    for item in os.listdir(temp_dir):
                        source = os.path.join(temp_dir, item)
                        destination = os.path.join(PROJECTS_DIR, item)
                        shutil.move(source, destination)

                    shutil.rmtree(temp_dir)

                print(f"{Fore.GREEN}Projects imported successfully from '{path}' as TAR.{Style.RESET_ALL}")
                return True

        except Exception as e:
            print(f"{Fore.YELLOW}Failed to extract '{path}': {e}{Style.RESET_ALL}")
        return False


    # First attempt: Try extracting the file as is (even with misleading extension)
    if try_extract(compressed_file_path, '.zip') or try_extract(compressed_file_path, '.tar.gz'):
        return

    # Attempt to guess the correct format by stripping the misleading extension and retrying
    base_path = os.path.splitext(compressed_file_path)[0]
    
    if try_extract(base_path + '.zip', '.zip') or try_extract(base_path + '.tar.gz', '.tar.gz'):
        return

    print(f"{Fore.RED}All extraction attempts failed. Please check the file format and try again.{Style.RESET_ALL}")


 
def choose_project():
    """Prompt the user to select a project from the list."""
    projects = list_projects()
    if not projects:
        print(f"{Fore.RED}No projects available.{Style.RESET_ALL}")
        return None
    
    return inquirer.select(message="Select a project:", choices=projects).execute()

def display_menu():
    """Display the main menu and get user choice."""
    options = [
        "Create a new project and copy .env",
        "Decrypt an encrypted .env file",
        "View encrypted files in a project",
        "Delete a project",
        "Compress projects folder for cloud upload",
        "Import projects from compressed file",
        "Exit"
    ]
    return inquirer.select("Select an option:", options).execute()

def main():
    """Main function to run the script."""
    ensure_projects_directory()

    while True:
        choice = display_menu()
        
        if choice == "Create a new project and copy .env":
            project_name = inquirer.text(message="Enter new project name:").execute()
            project_path = inquirer.text(message="Enter the full path of the project (where the .env files are located):").execute()
            create_project(project_name, project_path)

        elif choice == "Decrypt an encrypted .env file":
            project_name = choose_project()
            if project_name:
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

        elif choice == "Compress projects folder for cloud upload":
            compress_projects()

        elif choice == "Import projects from compressed file":
            import_projects()

        elif choice == "Exit":
            print(f"{Fore.CYAN}Exiting...{Style.RESET_ALL}")
            break


if __name__ == "__main__":
    main()
