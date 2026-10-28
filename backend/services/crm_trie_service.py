"""
CRM Trie Service - Prefix Tree Data Structure
Implements Trie data structure for O(L) instant autocomplete search
over Customer Names, Emails, and Phone Numbers per Company.

Zero-Downtime & Non-Destructive: Reads Customer models without DB mutations.
"""
from typing import List, Dict, Any, Optional
from models.customer import Customer

class CRMTrieNode:
    def __init__(self):
        self.children: Dict[str, 'CRMTrieNode'] = {}
        self.is_end_of_word: bool = False
        self.items: List[Dict[str, Any]] = []


class CRMSearchTrieService:
    """
    Trie Index per Company for O(L) Autocomplete Searches in CRM
    """
    _tries: Dict[int, CRMTrieNode] = {}  # company_id -> Root CRMTrieNode

    @classmethod
    def rebuild_trie_for_company(cls, company_id: int):
        """Build Trie index for a company from active customers in database"""
        root = CRMTrieNode()
        customers = Customer.query.filter_by(company_id=company_id).all()

        for customer in customers:
            customer_info = customer.to_dict() if hasattr(customer, 'to_dict') else {
                'id': customer.id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'phone': customer.phone,
                'lead_score': customer.lead_score
            }

            # Index terms
            search_terms = []
            if customer.first_name:
                search_terms.append(customer.first_name.lower())
            if customer.last_name:
                search_terms.append(customer.last_name.lower())
            if customer.first_name and customer.last_name:
                search_terms.append(f"{customer.first_name} {customer.last_name}".lower())
            if customer.email:
                search_terms.append(customer.email.lower())
            if customer.phone:
                search_terms.append(customer.phone.replace("+", "").replace(" ", ""))

            for term in search_terms:
                cls._insert_term(root, term, customer_info)

        cls._tries[company_id] = root
        return len(customers)

    @classmethod
    def _insert_term(cls, root: CRMTrieNode, term: str, customer_info: Dict[str, Any]):
        curr = root
        for char in term:
            if char not in curr.children:
                curr.children[char] = CRMTrieNode()
            curr = curr.children[char]
            # Keep up to 10 matching customers at intermediate nodes for fast prefix matches
            if not any(c['id'] == customer_info['id'] for c in curr.items):
                if len(curr.items) < 10:
                    curr.items.append(customer_info)
        curr.is_end_of_word = True

    @classmethod
    def search_prefix(cls, company_id: int, prefix: str) -> List[Dict[str, Any]]:
        """Search prefix in O(L) time where L is length of prefix"""
        if company_id not in cls._tries:
            cls.rebuild_trie_for_company(company_id)

        root = cls._tries.get(company_id)
        if not root:
            return []

        curr = root
        for char in prefix.lower():
            if char not in curr.children:
                return []
            curr = curr.children[char]

        return curr.items
