import os
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

HAVE_TRANSFORMERS = False
try:
    from sentence_transformers import SentenceTransformer
    HAVE_TRANSFORMERS = True
except Exception as err:
    logger.warning(f"SentenceTransformer import failed ({err}). Self-healing will use heuristic token matcher fallback.")

class SelfHealingLocator:
    _model_instance = None
    _model_failed = False

    @classmethod
    def get_model(cls):
        """
        Lazy load and cache the SentenceTransformer model (singleton)
        to prevent reloading on every self-healing invocation.
        """
        if not HAVE_TRANSFORMERS or cls._model_failed:
            return None

        if cls._model_instance is None:
            try:
                os.environ["HF_HOME"] = r"D:\hf_cache"
                os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"D:\hf_cache"
                
                logger.info("Initializing SentenceTransformer (all-MiniLM-L6-v2) on D: drive...")
                cls._model_instance = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("SentenceTransformer model successfully loaded.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer: {e}. Falling back to heuristic locator.")
                cls._model_failed = True
                return None
        return cls._model_instance

    @staticmethod
    def extract_interactive_elements(page) -> List[Dict[str, Any]]:
        """
        Executes JavaScript on the live page DOM to extract visible candidate interactive elements.
        Dynamically tags elements with data-healing-id if they lack standard ID/Name locators.
        """
        js_extract_script = """
        () => {
            const candidates = [];
            const elements = document.querySelectorAll(
                'button, input, select, textarea, a, h1, h2, h3, h4, h5, h6, p, [role="button"], [role="link"], [role="checkbox"], [role="radio"]'
            );
            
            elements.forEach((el, index) => {
                if (candidates.length >= 50) return;
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                
                // Only evaluate visible elements with actual physical dimensions
                if (rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none') {
                    const id = el.id || '';
                    const name = el.getAttribute('name') || '';
                    const placeholder = el.getAttribute('placeholder') || '';
                    const type = el.getAttribute('type') || '';
                    const role = el.getAttribute('role') || '';
                    const text = el.innerText || el.textContent || el.value || '';
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    
                    // Fetch associated label text if exists
                    let labelText = '';
                    if (el.labels && el.labels.length > 0) {
                        labelText = el.labels[0].innerText || el.labels[0].textContent || '';
                    } else if (id) {
                        const lbl = document.querySelector(`label[for="${id}"]`);
                        if (lbl) {
                            labelText = lbl.innerText || lbl.textContent || '';
                        }
                    }
                    
                    // Generate a unique locator selector
                    let selector = '';
                    if (id) {
                        selector = `#${id}`;
                    } else if (name) {
                        selector = `${el.tagName.toLowerCase()}[name="${name}"]`;
                    } else {
                        // Dynamically tag element with a healing-id to retrieve it reliably
                        el.setAttribute('data-healing-id', index.toString());
                        selector = `[data-healing-id="${index}"]`;
                    }
                    
                    candidates.push({
                        id: id,
                        tagName: el.tagName.toLowerCase(),
                        name: name,
                        placeholder: placeholder,
                        type: type,
                        role: role,
                        text: text.trim().substring(0, 100),
                        ariaLabel: ariaLabel,
                        label: labelText.trim(),
                        selector: selector
                    });
                }
            });
            return candidates;
        }
        """
        try:
            return page.evaluate(js_extract_script)
        except Exception as e:
            logger.error(f"Failed to scrape DOM elements: {e}")
            return []

    @classmethod
    def build_representation(cls, c: Dict[str, Any]) -> str:
        """
        Creates a semantic string representation of an interactive element.
        """
        parts = [
            f"element: {c['tagName']}",
            f"text: {c['text']}" if c['text'] else "",
            f"id: {c['id']}" if c['id'] else "",
            f"name: {c['name']}" if c['name'] else "",
            f"placeholder: {c['placeholder']}" if c['placeholder'] else "",
            f"label: {c['label']}" if c['label'] else "",
            f"role: {c['role']}" if c['role'] else "",
            f"type: {c['type']}" if c['type'] else "",
            f"aria-label: {c['ariaLabel']}" if c['ariaLabel'] else ""
        ]
        return " | ".join([p for p in parts if p])

    @classmethod
    def heal(cls, page, target_description: str, threshold: float = 0.40) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Inspects live page DOM candidates, encodes representations, calculates cosine
        similarities, and returns the highest matching candidate above the confidence threshold.
        """
        candidates = cls.extract_interactive_elements(page)
        if not candidates:
            logger.warning("No interactive elements found on the page to heal.")
            return None, 0.0

        model = cls.get_model()

        # Build descriptions for all elements
        candidate_reprs = [cls.build_representation(c) for c in candidates]

        if model is not None:
            # Calculate embeddings using SentenceTransformer
            target_embedding = model.encode(target_description, convert_to_tensor=True)
            candidate_embeddings = model.encode(candidate_reprs, convert_to_tensor=True)

            # Compute cosine similarities
            from sentence_transformers.util import cos_sim
            similarities = cos_sim(target_embedding, candidate_embeddings).cpu().numpy()[0]
        else:
            # Fallback heuristic matcher (Token + Jaccard similarity)
            from difflib import SequenceMatcher
            target_tokens = set(re.findall(r"\w+", target_description.lower()))
            similarities = []
            for cand_repr in candidate_reprs:
                cand_lower = cand_repr.lower()
                seq_ratio = SequenceMatcher(None, target_description.lower(), cand_lower).ratio()
                cand_tokens = set(re.findall(r"\w+", cand_lower))
                intersection = target_tokens.intersection(cand_tokens)
                union = target_tokens.union(cand_tokens)
                jaccard = len(intersection) / len(union) if union else 0.0
                overlap_bonus = sum(0.2 for t in target_tokens if len(t) > 2 and t in cand_lower)
                score = min(1.0, (seq_ratio * 0.3) + (jaccard * 0.5) + min(0.2, overlap_bonus))
                similarities.append(score)
            similarities = np.array(similarities)

        best_idx = np.argmax(similarities)
        best_score = float(similarities[best_idx])
        best_candidate = candidates[best_idx]

        logger.info(f"Self-healing match search for description '{target_description}':")
        logger.info(f"  Best Match: {cls.build_representation(best_candidate)}")
        logger.info(f"  Selector: {best_candidate['selector']}")
        logger.info(f"  Similarity Score: {best_score:.4f} (Threshold: {threshold:.4f})")

        if best_score >= threshold:
            return best_candidate, best_score
        else:
            logger.warning(f"Best match score {best_score:.4f} is below threshold {threshold:.4f}. Rejecting healing.")
            return None, best_score
