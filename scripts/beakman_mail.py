#!/usr/bin/env python3
"""Envía un correo como Beakman <beakman@kademy.net> por el SMTP de Zoho.

beakman@kademy.net es un alias del buzón root@kademy.net. La contraseña de aplicación
de Zoho sale del llavero (zoho/beakman-smtp) y nunca va en el comando ni en el repo.

Uso:
  scripts/beakman_mail.py --to <para> [--cc <copia>]... --subject <asunto> \\
      --text cuerpo.txt [--html cuerpo.html [--imagen <nombre>=<fichero.png>]...]

--imagen incrusta una imagen en el correo; el HTML la usa con <img src="cid:<nombre>">. Va dentro del
correo (no depende de ninguna web) y Gmail no recolorea las imágenes en modo oscuro: lo que tenga que
verse igual en tema claro y oscuro, como la cabecera de Beakman, va como imagen.
"""
import argparse
import mimetypes
import smtplib
import subprocess
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

SMTP_HOST, SMTP_PORT = "smtp.zoho.eu", 587
LOGIN = "root@kademy.net"
FROM = ("Beakman", "beakman@kademy.net")


def main():
    parser = argparse.ArgumentParser(description="Envía un correo como Beakman.")
    parser.add_argument("--to", required=True, action="append")
    parser.add_argument("--cc", default=[], action="append")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--text", required=True, help="cuerpo en texto plano")
    parser.add_argument("--html", help="cuerpo en HTML (opcional)")
    parser.add_argument("--imagen", default=[], action="append", help="nombre=fichero, para cid:nombre en el HTML")
    args = parser.parse_args()

    password = subprocess.run(
        ["secret-tool", "lookup", "service", "zoho", "name", "beakman-smtp"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not password:
        raise SystemExit("Falta zoho/beakman-smtp en el llavero.")

    msg = EmailMessage()
    msg["From"] = formataddr(FROM)
    msg["To"] = ", ".join(args.to)
    if args.cc:
        msg["Cc"] = ", ".join(args.cc)
    msg["Subject"] = args.subject
    msg["Message-ID"] = make_msgid(domain="kademy.net")
    with open(args.text, encoding="utf-8") as fh:
        msg.set_content(fh.read())
    if args.html:
        with open(args.html, encoding="utf-8") as fh:
            msg.add_alternative(fh.read(), subtype="html")
        html_part = msg.get_payload()[1]
        for imagen in args.imagen:
            nombre, fichero = imagen.split("=", 1)
            maintype, subtype = (mimetypes.guess_type(fichero)[0] or "image/png").split("/")
            with open(fichero, "rb") as fh:
                html_part.add_related(fh.read(), maintype=maintype, subtype=subtype, cid=f"<{nombre}>",
                                      disposition="inline", filename=fichero.rsplit("/", 1)[-1])
    elif args.imagen:
        raise SystemExit("--imagen necesita --html.")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(LOGIN, password)
        smtp.send_message(msg, from_addr=LOGIN, to_addrs=args.to + args.cc)
    print("enviado a", ", ".join(args.to + args.cc))


if __name__ == "__main__":
    main()
