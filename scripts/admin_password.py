#!/usr/bin/env python3
"""Huella scrypt de la contraseña de administración de Beakman (/admin), para BEAKMAN_ADMIN_HASH.

Pide la contraseña dos veces, sin mostrarla, y escribe en la salida solo la huella. La contraseña no se guarda en
ningún sitio. Para dejarla directamente en el secreto de GitHub del despliegue:

    scripts/admin_password.py | gh secret set BEAKMAN_ADMIN_HASH -R icalvete/kademy

Mismo formato que mcp/beakman_mcp/entrada.py (huella_clave / verificar_clave): «scrypt:n:r:p:sal:huella».
"""
import getpass
import hashlib
import secrets
import sys

clave = getpass.getpass("Contraseña de administración: ")
if len(clave) < 12:
    sys.exit("Mejor de 12 caracteres o más.")
if getpass.getpass("Otra vez: ") != clave:
    sys.exit("No coinciden.")
sal = secrets.token_bytes(16)
n, r, p = 2 ** 15, 8, 1
h = hashlib.scrypt(clave.encode(), salt=sal, n=n, r=r, p=p, maxmem=64 * 1024 * 1024)
sys.stdout.write(f"scrypt:{n}:{r}:{p}:{sal.hex()}:{h.hex()}")
