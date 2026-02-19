"""
Vues pour le traitement des documents
"""
import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pathlib import Path

from .document_processing import get_document_processing_service

logger = logging.getLogger('views.document_processing')


def is_admin(user):
    """Vérifie si l'utilisateur est admin"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def document_processing_dashboard(request):
    """
    Dashboard de traitement des documents
    """
    service = get_document_processing_service()
    stats = service.get_processing_stats()
    
    context = {
        'stats': stats,
        'page_title': 'Traitement de Documents'
    }
    
    return render(request, 'chat/document_processing.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def upload_and_process_pdf(request):
    """
    Upload et traite un PDF
    """
    try:
        # Récupère le fichier
        if 'pdf_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Aucun fichier fourni'
            }, status=400)
        
        pdf_file = request.FILES['pdf_file']
        
        # Métadonnées optionnelles
        metadata = {}
        if request.POST.get('title'):
            metadata['title'] = request.POST.get('title')
        if request.POST.get('author'):
            metadata['author'] = [a.strip() for a in request.POST.get('author').split(',')]
        if request.POST.get('subject'):
            metadata['subject'] = request.POST.get('subject')
        if request.POST.get('keywords'):
            metadata['keywords'] = [k.strip() for k in request.POST.get('keywords').split(',')]
        
        # Sauvegarde temporaire
        service = get_document_processing_service()
        pdf_path = service.raw_dir / pdf_file.name
        
        with open(pdf_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        
        logger.info(f"📄 Fichier uploadé: {pdf_file.name}")
        
        # Traite le document
        upload_to_pinecone = request.POST.get('upload_to_pinecone', 'true').lower() == 'true'
        
        stats = service.process_pdf(
            str(pdf_path),
            metadata=metadata if metadata else None,
            upload_to_pinecone=upload_to_pinecone,
            user_id=request.user.id,
            is_public=True  # Admin uploads are public by default
        )
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'message': f'Document {pdf_file.name} traité avec succès!'
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def process_existing_pdfs(request):
    """
    Traite tous les PDFs existants dans data/raw
    """
    try:
        service = get_document_processing_service()
        upload_to_pinecone = request.POST.get('upload_to_pinecone', 'true').lower() == 'true'
        
        results = service.process_directory(
            str(service.raw_dir),
            upload_to_pinecone=upload_to_pinecone,
            user_id=request.user.id,
            is_public=True
        )
        
        success_count = sum(1 for r in results if not r.get('errors'))
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total': len(results),
            'success_count': success_count,
            'message': f'{success_count}/{len(results)} documents traités avec succès'
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement batch: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_admin)
def get_processing_status(request):
    """
    Retourne le statut actuel du traitement
    """
    service = get_document_processing_service()
    stats = service.get_processing_stats()
    
    return JsonResponse({
        'success': True,
        'stats': stats
    })
