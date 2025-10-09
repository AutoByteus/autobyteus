import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)


class CertificateError(Exception):
    """Custom exception for certificate-related errors."""


def get_certificate_info(cert_path: Union[str, Path]) -> Dict[str, object]:
    """
    Retrieve certificate information including fingerprint and validity window.
    """
    try:
        cert_path = Path(cert_path)
        cert_data = cert_path.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        cert_der = cert.fingerprint(hashes.SHA256())
        fingerprint = ":".join(f"{byte:02X}" for byte in cert_der)

        now = datetime.utcnow()
        days_until_expiry = (cert.not_valid_after - now).days

        return {
            "subject": cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
                0
            ].value,
            "issuer": cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
                0
            ].value,
            "valid_from": cert.not_valid_before,
            "valid_until": cert.not_valid_after,
            "fingerprint": fingerprint,
            "is_valid": cert.not_valid_before < now < cert.not_valid_after,
            "days_until_expiry": days_until_expiry,
            "cert_data": cert_data,
            "cert": cert,
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        raise CertificateError(f"Failed to get certificate info: {exc}") from exc


def verify_certificate(
    cert_path: Union[str, Path],
    expected_fingerprint: Optional[str] = None,
    warn_expiry_days: int = 30,
) -> Dict[str, object]:
    """
    Verify the certificate's validity and optional fingerprint match.
    """
    try:
        info = get_certificate_info(cert_path)

        if not info["is_valid"]:
            if datetime.utcnow() < info["valid_from"]:
                raise CertificateError("Certificate is not yet valid")
            raise CertificateError(
                f"Certificate has expired on {info['valid_until'].strftime('%Y-%m-%d')}"
            )

        if expected_fingerprint:
            expected = expected_fingerprint.replace(" ", "").upper()
            actual = str(info["fingerprint"]).replace(" ", "")
            if actual != expected:
                raise CertificateError(
                    "Certificate fingerprint mismatch. "
                    f"Expected: {expected}\nGot: {actual}"
                )
            logger.info("Certificate fingerprint verified successfully")
        else:
            logger.warning(
                "Certificate fingerprint verification skipped. "
                "Set AUTOBYTEUS_CERT_FINGERPRINT to enable this security feature. "
                "Current certificate fingerprint: %s",
                info["fingerprint"],
            )

        logger.info(
            "Certificate valid from %s to %s",
            info["valid_from"],
            info["valid_until"],
        )
        logger.info("Certificate fingerprint (SHA256): %s", info["fingerprint"])
        logger.info("Certificate subject: %s", info["subject"])

        if info["days_until_expiry"] <= warn_expiry_days:
            logger.warning(
                "Certificate will expire in %s days on %s",
                info["days_until_expiry"],
                info["valid_until"].strftime("%Y-%m-%d"),
            )

        return info
    except CertificateError:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        raise CertificateError(f"Certificate verification failed: {exc}") from exc
