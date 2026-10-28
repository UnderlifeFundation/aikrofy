"""
Lead Heap Service - High Performance Max-Heap Engine
Implements Max-Heap (heapq) algorithms for O(1) priority access
to High-Intent Sales Leads for CSO (Chief Sales Officer) and CRO (Chief Revenue Officer).

Zero-Downtime & Non-Destructive: Operates seamlessly on existing Customer models.
"""
import heapq
import time
from typing import List, Dict, Optional, Any
from models.customer import Customer

class CustomerHeapItem:
    """Wrapper to enable Max-Heap comparison in heapq (invert lead_score for min-heap behavior)"""
    def __init__(self, customer: Customer):
        self.customer = customer
        # lead_score is 0 to 100. Invert so highest score comes first in min-heap.
        self.priority = -(customer.lead_score or 0)
        self.timestamp = customer.created_at.timestamp() if getattr(customer, 'created_at', None) else time.time()

    def __lt__(self, other):
        if self.priority == other.priority:
            return self.timestamp < other.timestamp  # Earliest lead breaks ties
        return self.priority < other.priority


class LeadPriorityHeapService:
    """
    In-Memory Max-Heap Service for Lead Scoring & CSO Sales Triage (O(1) Top Access)
    """
    _heaps: Dict[int, List[CustomerHeapItem]] = {}  # company_id -> Heap List

    @classmethod
    def rebuild_heap_for_company(cls, company_id: int):
        """Build or refresh the Max-Heap for a company from database"""
        customers = Customer.query.filter_by(company_id=company_id).all()
        
        heap_list = [CustomerHeapItem(c) for c in customers]
        heapq.heapify(heap_list)
        cls._heaps[company_id] = heap_list
        return len(heap_list)

    @classmethod
    def get_top_lead(cls, company_id: int) -> Optional[Customer]:
        """Get highest scoring customer lead in O(1) time"""
        if company_id not in cls._heaps or not cls._heaps[company_id]:
            cls.rebuild_heap_for_company(company_id)

        heap = cls._heaps.get(company_id, [])
        if heap:
            return heap[0].customer  # O(1) root inspection
        return None

    @classmethod
    def pop_top_lead(cls, company_id: int) -> Optional[Customer]:
        """Extract highest scoring lead in O(log N) time"""
        if company_id not in cls._heaps or not cls._heaps[company_id]:
            cls.rebuild_heap_for_company(company_id)

        heap = cls._heaps.get(company_id, [])
        if heap:
            item = heapq.heappop(heap)
            return item.customer
        return None

    @classmethod
    def add_or_update_customer(cls, customer: Customer):
        """Insert or refresh a customer in the company's heap in O(log N) time"""
        company_id = customer.company_id
        if company_id not in cls._heaps:
            cls.rebuild_heap_for_company(company_id)
        
        item = CustomerHeapItem(customer)
        heapq.heappush(cls._heaps[company_id], item)
