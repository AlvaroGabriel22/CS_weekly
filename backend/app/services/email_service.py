"""Envio de e-mail (SMTP) — estrutura completa, servidor plugável via .env.

Enquanto SMTP_HOST estiver vazio, is_configured() é False e o endpoint de
envio devolve 503 com mensagem clara; nada mais quebra.
"""

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.SMTP_HOST)

    def send(
        self,
        to: list[str],
        subject: str,
        body: str,
        attachment_path: str | None = None,
        attachment_name: str | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Envia o e-mail (texto simples) com anexo opcional. Levanta exceção
        em falha de SMTP — o chamador converte em erro amigável."""
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM or settings.SMTP_USER
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to
        message.set_content(body)

        if attachment_path:
            path = Path(attachment_path)
            if path.exists():
                message.add_attachment(
                    path.read_bytes(),
                    maintype="application",
                    subtype="vnd.openxmlformats-officedocument.presentationml.presentation",
                    filename=attachment_name or path.name,
                )

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("E-mail enviado | para=%s | assunto=%s", to, subject[:60])
