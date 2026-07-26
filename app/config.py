"""
Central configuration, driven entirely by environment variables.

See .env.example for the variables this app understands.
"""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    STEGO_BASE_DIR = os.environ.get("STEGO_BASE_DIR")

    # Raw upload size limit (bytes). Raised from the original 32MB default -
    # a high-resolution PNG can exceed that easily. Override with the
    # MAX_UPLOAD_MB env var if your host has less RAM to spare.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "64")) * 1024 * 1024

    # Cover image resolution limit (megapixels). The original hardcoded 4MP
    # cap was sized for a 512MB host. Raised to a more generous default that
    # still leaves headroom on a 12GB VM; override with MAX_IMAGE_MEGAPIXELS
    # if you deploy somewhere smaller.
    MAX_IMAGE_MEGAPIXELS = float(os.environ.get("MAX_IMAGE_MEGAPIXELS", "30"))

    @staticmethod
    def validate():
        """
        Fail loudly instead of silently falling back to a shared/hardcoded
        secret key. A hardcoded dev key that accidentally ships to
        production is a real security hole, so we refuse to start instead.
        """
        if not Config.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable is not set.\n"
                "Generate one, e.g.: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "then export SECRET_KEY=<value> (or add it to your .env / systemd unit / "
                "hosting provider's env vars) before starting the app."
            )

