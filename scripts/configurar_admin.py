import getpass
import secrets

from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def main():
    print()
    print("========================================")
    print(" CONFIGURACIÓN ADMINISTRADOR")
    print("========================================")
    print()

    username = input(
        "Usuario administrador [admin]: "
    ).strip()

    if not username:
        username = "admin"

    password = getpass.getpass(
        "Contraseña: "
    )

    password_confirmacion = getpass.getpass(
        "Repite la contraseña: "
    )

    if not password:
        print()
        print("ERROR: La contraseña no puede estar vacía.")
        return

    if password != password_confirmacion:
        print()
        print("ERROR: Las contraseñas no coinciden.")
        return

    password_hash = password_hasher.hash(
        password
    )

    jwt_secret = secrets.token_hex(
        32
    )

    print()
    print("========================================")
    print(" COPIA ESTO EN TU .env")
    print("========================================")
    print()

    print(
        f"ADMIN_USERNAME={username}"
    )

    print(
        f"ADMIN_PASSWORD_HASH={password_hash}"
    )

    print(
        f"JWT_SECRET={jwt_secret}"
    )

    print(
        "ACCESS_TOKEN_EXPIRE_MINUTES=60"
    )

    print()
    print(
        "No compartas ADMIN_PASSWORD_HASH "
        "ni JWT_SECRET."
    )
    print()


if __name__ == "__main__":
    main()