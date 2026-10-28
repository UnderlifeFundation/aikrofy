from routing import current_app
"""
Sentiment Analysis Service
Analyzes message sentiment using LLM
"""
import os
from typing import Optional, Dict, Any, List



class SentimentService:
    """
    Sentiment Analysis Service using LLM
    Analyzes text for sentiment and emotional tone
    """
    
    # Sentiment categories
    POSITIVE = 'positive'
    NEUTRAL = 'neutral'
    NEGATIVE = 'negative'
    
    # Keywords that suggest escalation
    ESCALATION_KEYWORDS = [
        'hablar con humano', 'persona real', 'gerente', 'supervisor',
        'queja', 'denuncia', 'demanda', 'abogado', 'legal',
        'furioso', 'enojado', 'molesto', 'frustrado',
        'cancelar', 'reembolso', 'devolver dinero',
        'speak to human', 'real person', 'manager', 'supervisor',
        'complaint', 'lawsuit', 'lawyer', 'legal action',
        'angry', 'upset', 'frustrated', 'furious',
        'cancel', 'refund', 'money back'
    ]
    
    def __init__(self, company=None):
        self.company = company
        self._llm_service = None
    
    def _get_llm_service(self):
        """Lazy load LLM service"""
        if not self._llm_service:
            from services.llm_service import LLMService
            self._llm_service = LLMService(self.company)
        return self._llm_service
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text message
        
        Args:
            text: Text to analyze
        
        Returns:
            Sentiment analysis result with score, category, and reasoning
        """
        if not text or not text.strip():
            return {
                'score': 0.0,
                'category': self.NEUTRAL,
                'confidence': 1.0,
                'reasoning': 'Empty text'
            }
        
        # Quick keyword check for escalation
        text_lower = text.lower()
        has_escalation_keyword = any(kw in text_lower for kw in self.ESCALATION_KEYWORDS)
        
        try:
            llm_service = self._get_llm_service()
            
            analysis_prompt = f"""Analyze the sentiment of the following message and respond in JSON format.

Message: "{text}"

Respond with ONLY valid JSON in this exact format:
{{
    "score": <float from -1.0 (very negative) to 1.0 (very positive)>,
    "category": "<positive|neutral|negative>",
    "confidence": <float from 0.0 to 1.0>,
    "reasoning": "<brief explanation>",
    "escalation_risk": <true|false>,
    "emotions": ["<list of detected emotions>"]
}}"""

            messages = [
                {"role": "system", "content": "You are a sentiment analysis expert. Always respond with valid JSON only."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = llm_service.chat_completion(
                messages=messages,
                model='gpt-5-nano',
                temperature=0.1,
                max_tokens=200
            )
            
            # Parse JSON response
            import json
            content = response.get('content', '{}')
            
            # Clean up response (remove markdown code blocks if present)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            result = json.loads(content.strip())
            
            # Ensure all fields exist
            result.setdefault('score', 0.0)
            result.setdefault('category', self.NEUTRAL)
            result.setdefault('confidence', 0.8)
            result.setdefault('reasoning', '')
            result.setdefault('escalation_risk', has_escalation_keyword)
            result.setdefault('emotions', [])
            
            # Override escalation_risk if keyword detected
            if has_escalation_keyword:
                result['escalation_risk'] = True
            
            return result
            
        except Exception as e:
            # Fallback: simple keyword-based analysis
            return self._fallback_analysis(text, has_escalation_keyword)
    
    def _fallback_analysis(self, text: str, has_escalation_keyword: bool) -> Dict[str, Any]:
        """Simple keyword-based fallback when LLM fails"""
        text_lower = text.lower()
        
        # Simple positive/negative word lists
        positive_words = ['gracias', 'excelente', 'genial', 'perfecto', 'bueno', 'encanta',
                         'thank', 'great', 'excellent', 'perfect', 'good', 'love', 'amazing']
        negative_words = ['malo', 'terrible', 'horrible', 'odio', 'peor', 'nunca',
                         'bad', 'terrible', 'horrible', 'hate', 'worst', 'never', 'awful']
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        if neg_count > pos_count:
            score = -0.5 - (0.1 * min(neg_count, 5))
            category = self.NEGATIVE
        elif pos_count > neg_count:
            score = 0.5 + (0.1 * min(pos_count, 5))
            category = self.POSITIVE
        else:
            score = 0.0
            category = self.NEUTRAL
        
        return {
            'score': max(-1.0, min(1.0, score)),
            'category': category,
            'confidence': 0.5,
            'reasoning': 'Keyword-based fallback analysis',
            'escalation_risk': has_escalation_keyword or score < -0.5,
            'emotions': []
        }
    
    def analyze_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze overall sentiment of a conversation
        
        Args:
            messages: List of messages with 'role' and 'content' keys
        
        Returns:
            Aggregate sentiment analysis
        """
        if not messages:
            return {
                'overall_score': 0.0,
                'overall_category': self.NEUTRAL,
                'trend': 'stable',
                'escalation_risk': False,
                'message_sentiments': []
            }
        
        # Analyze only user messages
        user_messages = [m for m in messages if m.get('role') == 'user']
        
        if not user_messages:
            return {
                'overall_score': 0.0,
                'overall_category': self.NEUTRAL,
                'trend': 'stable',
                'escalation_risk': False,
                'message_sentiments': []
            }
        
        # Analyze each message
        sentiments = []
        for msg in user_messages[-5:]:  # Only last 5 messages
            analysis = self.analyze_text(msg.get('content', ''))
            sentiments.append(analysis)
        
        # Calculate aggregates
        scores = [s['score'] for s in sentiments]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Determine trend (comparing last vs first half)
        if len(scores) >= 2:
            first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if second_half_avg > first_half_avg + 0.2:
                trend = 'improving'
            elif second_half_avg < first_half_avg - 0.2:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Determine category
        if avg_score > 0.3:
            category = self.POSITIVE
        elif avg_score < -0.3:
            category = self.NEGATIVE
        else:
            category = self.NEUTRAL
        
        # Check for escalation
        escalation_risk = any(s.get('escalation_risk', False) for s in sentiments)
        
        return {
            'overall_score': round(avg_score, 2),
            'overall_category': category,
            'trend': trend,
            'escalation_risk': escalation_risk,
            'message_sentiments': sentiments
        }
    
    def should_escalate(self, sentiment_result: Dict[str, Any]) -> bool:
        """
        Determine if a conversation should be escalated based on sentiment
        
        Args:
            sentiment_result: Result from analyze_text or analyze_conversation
        
        Returns:
            True if escalation is recommended
        """
        # Direct escalation risk flag
        if sentiment_result.get('escalation_risk', False):
            return True
        
        # Very negative sentiment
        score = sentiment_result.get('score') or sentiment_result.get('overall_score', 0)
        if score < -0.7:
            return True
        
        # Declining trend with negative sentiment
        if sentiment_result.get('trend') == 'declining' and score < -0.3:
            return True
        
        return False
