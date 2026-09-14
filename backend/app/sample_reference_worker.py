"""Independent reconciliation, with 60 seconds idle between completed passes."""
import logging
import signal
from threading import Event
from app.db import get_reference_sessionmaker
from app.sample_reference_config import load_reference_config
from app.sample_reference_service import reconcile_registered

logger=logging.getLogger(__name__)

def reconcile_once(factory=None,config=None):
    config=config if config is not None else load_reference_config()
    if not config.enabled: return {}
    return reconcile_registered(factory or get_reference_sessionmaker(),config)

def main():
    stopped=Event()
    for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,lambda *_:stopped.set())
    while not stopped.is_set():
        try:
            result=reconcile_once()
            if any(status not in ("ready","superseded") for status in result.values()):
                logger.warning("sample-reference projection has unavailable sources")
        except Exception:
            logger.warning("sample-reference configuration or database unavailable")
        stopped.wait(60)

if __name__=="__main__": main()
