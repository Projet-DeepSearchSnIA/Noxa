"""
Templates de prompts pour le système RAG
Optimisés pour citation de sources et qualité des réponses
"""
from typing import List, Dict, Optional


class PromptTemplates:
    """Templates de prompts pour différents cas d'usage"""
    
    # Template principal RAG avec sources
    RAG_WITH_SOURCES = """Tu es un assistant expert qui répond aux questions en te basant UNIQUEMENT sur les documents fournis.

RÈGLES IMPORTANTES:
1. Réponds UNIQUEMENT avec les informations présentes dans les documents ci-dessous
2. Si l'information n'est PAS dans les documents, dis clairement "Je ne trouve pas cette information dans les documents fournis"
3. CITE TOUJOURS tes sources en utilisant le format [Source: nom_du_document, page X]
4. Sois précis et factuel
5. Si plusieurs documents disent des choses différentes, mentionne les deux points de vue

DOCUMENTS DE RÉFÉRENCE:
{context}

QUESTION DE L'UTILISATEUR:
{question}

RÉPONSE (avec citations):"""

    # Template pour synthèse multi-documents
    MULTI_DOC_SYNTHESIS = """Tu es un assistant expert en synthèse documentaire.

Ta tâche est de synthétiser les informations des documents suivants pour répondre à la question.

DOCUMENTS:
{context}

QUESTION:
{question}

Fournis une réponse complète qui:
1. Synthétise les informations de TOUS les documents pertinents
2. Cite chaque source utilisée avec [Source: document, page X]
3. Signale les contradictions éventuelles entre documents
4. Reste factuel et objective

RÉPONSE:"""

    # Template pour questions sans contexte (fallback)
    NO_CONTEXT = """Tu es un assistant utile.

L'utilisateur pose la question suivante, mais aucun document pertinent n'a été trouvé dans la base de connaissances.

QUESTION:
{question}

Réponds de manière générale en précisant que tu n'as pas de documents spécifiques sur ce sujet dans la base de connaissances.

RÉPONSE:"""

    # Template pour vérification de pertinence
    RELEVANCE_CHECK = """Les documents suivants sont-ils pertinents pour répondre à la question?

QUESTION: {question}

DOCUMENTS:
{context}

Réponds uniquement par OUI ou NON."""

    @staticmethod
    def format_context(
        retrieved_chunks: List[Dict],
        include_scores: bool = False,
        max_chunks: int = 5
    ) -> str:
        """
        Formate les chunks récupérés en contexte structuré
        
        Args:
            retrieved_chunks: Liste de chunks avec metadata
            include_scores: Inclure les scores de similarité
            max_chunks: Nombre max de chunks à inclure
            
        Returns:
            Contexte formaté
        """
        context_parts = []
        
        for i, chunk in enumerate(retrieved_chunks[:max_chunks], 1):
            # Supporte dict ou EnrichedChunk
            if hasattr(chunk, "to_dict"):
                chunk_dict = chunk.to_dict()
                metadata = getattr(chunk, "metadata", {}) or {}
                text = chunk_dict.get("text", "")
                score_val = chunk_dict.get("score")
            else:
                chunk_dict = chunk
                metadata = chunk.get('metadata', {})
                text = chunk.get('text', chunk.get('content', ''))
                score_val = chunk.get('score')
            
            # Informations de source
            doc_path = metadata.get('document_path') or metadata.get('document_name') or 'Document inconnu'
            pages = metadata.get('page_numbers', 'Page inconnue')
            
            # Format pages
            if isinstance(pages, list):
                pages_str = f"pages {', '.join(map(str, pages))}"
            elif isinstance(pages, str):
                pages_str = f"page {pages.replace('[', '').replace(']', '')}"
            else:
                pages_str = f"page {pages}"
            
            # Score optionnel
            score_str = ""
            if include_scores and score_val is not None:
                score_str = f" (pertinence: {score_val:.2f})"
            
            # Texte du chunk déjà déterminé

            # Images et formules (si disponibles)
            images = metadata.get('image_paths') or metadata.get('image_ids') or []
            formulas = metadata.get('formulas_latex') or []
            images_str = ""
            formulas_str = ""
            if images:
                if isinstance(images, list):
                    images_str = "\nImages: " + " | ".join([str(i) for i in images[:5]])
                else:
                    images_str = f"\nImages: {images}"
            if formulas:
                if isinstance(formulas, list):
                    formulas_str = "\nFormules: " + " | ".join([str(f) for f in formulas[:3]])
                else:
                    formulas_str = f"\nFormules: {formulas}"
            
            # Construction du bloc
            context_parts.append(
                f"--- Document {i} ---\n"
                f"Source: {doc_path}, {pages_str}{score_str}\n"
                f"Contenu:\n{text}\n"
                f"{images_str}"
                f"{formulas_str}\n"
            )
        
        return "\n".join(context_parts)
    
    @staticmethod
    def build_rag_prompt(
        question: str,
        retrieved_chunks: List[Dict],
        template: str = None,
        **kwargs
    ) -> str:
        """
        Construit le prompt RAG complet
        
        Args:
            question: Question de l'utilisateur
            retrieved_chunks: Chunks récupérés
            template: Template personnalisé (optionnel)
            **kwargs: Arguments additionnels pour le template
            
        Returns:
            Prompt complet
        """
        if template is None:
            template = PromptTemplates.RAG_WITH_SOURCES
        
        # Formate le contexte
        context = PromptTemplates.format_context(
            retrieved_chunks,
            include_scores=kwargs.get('include_scores', False),
            max_chunks=kwargs.get('max_chunks', 5)
        )
        
        # Construit le prompt
        prompt = template.format(
            context=context,
            question=question,
            **kwargs
        )
        
        return prompt
    
    @staticmethod
    def build_chat_messages(
        question: str,
        retrieved_chunks: List[Dict],
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        topic: Optional[str] = None,
        template: Optional[str] = None
    ) -> List[Dict]:
        """
        Construit les messages pour chat API (format OpenAI)
        
        Args:
            question: Question actuelle
            retrieved_chunks: Chunks récupérés
            system_prompt: Prompt système personnalisé
            conversation_history: Historique de conversation
            
        Returns:
            Liste de messages au format chat
        """
        messages = []
        
        # System prompt
        if system_prompt is None:
            context = PromptTemplates.format_context(retrieved_chunks)
            context_noxa = f"Tu es Noxa AI, l'IA intégrée dans Noxa. Noxa est une application permettant d'aider les les étudiants et chercheurs dans la rédaction de leurs documents académiques et scientifiques, sur divers domaines tels que la mathématiques, l'économie, la statistique, la physique, la chimie, la biologie, etc. Tu dois toujours répondre dans la langue de l'utilisateur."
            topic_line = f"Tu es spécialisé en {topic}." if topic else "Tu es un assistant expert."
            system_prompt = f"""{topic_line} {context_noxa} Tu réponds en te basant UNIQUEMENT sur les documents fournis. Adapte le style du texte selon les besoins

FORMAT DE RÉPONSE OBLIGATOIRE:
1) Réponse structurée et concise en texte.
2) NE PAS écrire de phrase d'introduction sur tes sources (ex: "Mes sources sont...", "Je m'appuie sur..."). Les citations sont obligatoires dans le texte via le format [Source: ...].
3) Toute équation doit être entourée par $$ ... $$ (LaTeX).
4) À la fin de ta réponse, ajoute **OBLIGATOIREMENT et SILENCIEUSEMENT** ces blocs pour le système :
   SOURCES_USED: [document1.pdf, document2.pdf]
   IMAGES_USED: [id_image1, id_image2]
   FOLLOW_UP_QUESTIONS: [Question 1; Question 2; Question 3]
5) Cite toujours tes sources dans le texte: [Source: document_path, page X]
6) Si l'info n'est pas dans les documents, dis-le clairement.
7) Propose 3 à 5 questions courtes et pertinentes en FOLLOW_UP_QUESTIONS.

DOCUMENTS DE RÉFÉRENCE:
{context}
"""
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Historique de conversation
        if conversation_history:
            messages.extend(conversation_history)
        
        # Question actuelle
        messages.append({
            "role": "user",
            "content": question
        })
        
        return messages
    
    @staticmethod
    def extract_sources_from_response(response: str) -> List[str]:
        """
        Extrait les sources citées d'une réponse
        
        Args:
            response: Réponse du LLM
            
        Returns:
            Liste des sources citées
        """
        import re
        
        # Pattern pour [Source: ...]
        pattern = r'\[Source:\s*([^\]]+)\]'
        sources = re.findall(pattern, response)
        
        return list(set(sources))  # Déduplique
    
    @staticmethod
    def extract_metadata_blocks(response: str) -> Dict:
        """
        Extrait et retire les blocs de métadonnées de la réponse.
        Gère les formats : TAG: [item1, item2] ou TAG: item1, item2
        """
        import re
        
        metadata = {
            'sources_used': [],
            'images_used': [],
            'equations_used': [],
            'follow_up_questions': []
        }
        
        clean_response = response
        
        # 1. Extraction des blocs avec ou sans crochets
        # Cette regex capture "TAG: content" jusqu'à la fin de la ligne ou le prochain TAG
        tags = ['SOURCES_USED', 'IMAGES_USED', 'EQUATIONS_USED', 'FOLLOW_UP_QUESTIONS']
        
        for key in metadata.keys():
            tag_name = key.upper()
            # Match le tag et son contenu jusqu'au prochain tag connu ou la fin
            # Supporte TAG: [content] et TAG: content
            pattern = rf'{tag_name}\s*:\s*(?:\[(.*?)\]|(.*?))(?=\s*(?:SOURCES_USED|IMAGES_USED|EQUATIONS_USED|FOLLOW_UP_QUESTIONS)|$)'
            
            match = re.search(pattern, clean_response, re.DOTALL | re.IGNORECASE)
            if match:
                full_match = match.group(0)
                # On prend soit le contenu entre crochets (group 1) soit le reste (group 2)
                content = (match.group(1) or match.group(2) or "").strip()
                
                # Parse la liste (split par , ou ; ou retour à la ligne)
                items = [item.strip() for item in re.split(r'[;,\n]', content) if item.strip()]
                # Nettoyage supplémentaire pour enlever les crochets résiduels si group 2 a été utilisé
                items = [item.strip('[] ') for item in items]
                metadata[key] = [i for i in items if i]
                
                # Retire le bloc de la réponse
                clean_response = clean_response.replace(full_match, '')
        
        # Nettoyage final des espaces multiples et lignes vides
        clean_response = re.sub(r'\n{3,}', '\n\n', clean_response).strip()
        
        return {
            'clean_response': clean_response,
            'metadata': metadata
        }
    
    @staticmethod
    def format_response_with_sources(
        response: str,
        retrieved_chunks: List[Dict]
    ) -> Dict:
        """
        Formate la réponse avec métadonnées des sources
        
        Args:
            response: Réponse du LLM
            retrieved_chunks: Chunks utilisés
            
        Returns:
            Dict avec réponse et sources détaillées
        """
        # Parse et nettoie la réponse
        parsed_result = PromptTemplates.extract_metadata_blocks(response)
        clean_response = parsed_result['clean_response']
        metadata = parsed_result['metadata']
        
        # Extrait les sources citées (soit du texte, soit du bloc metadata si présent)
        cited_sources = PromptTemplates.extract_sources_from_response(clean_response)
        if metadata['sources_used']:
            cited_sources.extend(metadata['sources_used'])
        cited_sources = list(set(cited_sources))
        
        # Collecte les infos des sources
        sources_info = []
        for chunk in retrieved_chunks:
            if hasattr(chunk, "to_dict"):
                chunk_dict = chunk.to_dict()
                metadata_chunk = getattr(chunk, "metadata", {}) or {}
                chunk_id = chunk_dict.get("chunk_id", "")
                score_val = chunk_dict.get("score", 0.0)
            else:
                chunk_dict = chunk
                metadata_chunk = chunk.get('metadata', {})
                chunk_id = chunk.get('id', '')
                score_val = chunk.get('score', 0.0)
            
            doc_name = metadata_chunk.get('document_name', '')
            pages = metadata_chunk.get('page_numbers', '')
            
            source_info = {
                'document': doc_name,
                'pages': pages,
                'chunk_id': chunk_id,
                'score': score_val
            }
            
            if source_info not in sources_info:
                sources_info.append(source_info)
        
        return {
            'response': clean_response,  # Texte nettoyé sans métadonnées
            'cited_sources': cited_sources,
            'all_sources': sources_info,
            'num_sources_used': len(retrieved_chunks),
            'extracted_metadata': metadata  # Métadonnées structurées
        }


# Templates prédéfinis pour différents types de questions

QUESTION_TYPE_TEMPLATES = {
    'factual': """Réponds à cette question factuelle en te basant sur les documents:

DOCUMENTS:
{context}

QUESTION: {question}

Réponse courte et précise avec source:""",
    
    'explanation': """Explique le concept suivant en te basant sur les documents:

DOCUMENTS:
{context}

QUESTION: {question}

Explication détaillée avec exemples et sources:""",
    
    'comparison': """Compare les éléments mentionnés en te basant sur les documents:

DOCUMENTS:
{context}

QUESTION: {question}

Comparaison structurée avec sources pour chaque point:""",
    
    'summary': """Fais une synthèse en te basant sur les documents:

DOCUMENTS:
{context}

QUESTION: {question}

Synthèse concise avec points clés et sources:"""
}


def get_template_for_question_type(question: str) -> str:
    """
    Sélectionne le template approprié selon le type de question
    
    Args:
        question: Question de l'utilisateur
        
    Returns:
        Template approprié
    """
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['comparer', 'différence', 'versus', 'vs']):
        return QUESTION_TYPE_TEMPLATES['comparison']
    
    elif any(word in question_lower for word in ['expliquer', 'comment', 'pourquoi', "c'est quoi"]):
        return QUESTION_TYPE_TEMPLATES['explanation']
    
    elif any(word in question_lower for word in ['résumer', 'synthèse', 'résumé', 'principaux points']):
        return QUESTION_TYPE_TEMPLATES['summary']
    
    elif any(word in question_lower for word in ['qui', 'quoi', 'où', 'quand', 'combien']):
        return QUESTION_TYPE_TEMPLATES['factual']
    
    else:
        return PromptTemplates.RAG_WITH_SOURCES
