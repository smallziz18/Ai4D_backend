#!/usr/bin/env python
"""
Point d'entrée personnalisé pour le serveur Uvicorn
Résout les conflits de gestion de signaux avec rich-toolkit
"""
import asyncio
import signal
import sys
import os

# Ajouter le répertoire courant au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_server():
    """Lance le serveur Uvicorn avec une gestion correcte des signaux"""
    try:
        import uvicorn
        from src import app

        # Configuration du serveur
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["src"],
            log_level="info",
        )

        # Créer le serveur
        server = uvicorn.Server(config)

        # Gérer les signaux de manière appropriée
        def signal_handler(sig, frame):
            """Gère proprement l'arrêt du serveur"""
            print("\nArrêt du serveur...")
            asyncio.create_task(server.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Lancer le serveur
        asyncio.run(server.serve())

    except KeyboardInterrupt:
        print("\nServeur interrompu par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_server()

