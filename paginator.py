"""
Sistema de Paginação - Velox
Similar ao django.core.paginator
"""

from typing import List, Any, Optional


class Paginator:
    """Sistema de paginação"""
    
    def __init__(self, object_list: List[Any], per_page: int, orphans: int = 3):
        self.object_list = list(object_list)
        self.per_page = per_page
        self.orphans = orphans
        self._count = len(object_list)
    
    def page(self, number: int) -> 'Page':
        """Retorna uma página específica"""
        number = int(number)
        if number < 1:
            number = 1
        if number > self.num_pages:
            number = self.num_pages
        start = (number - 1) * self.per_page
        end = start + self.per_page
        return Page(self.object_list[start:end], number, self)
    
    @property
    def num_pages(self) -> int:
        """Número total de páginas"""
        if self._count == 0:
            return 0
        return -(-self._count // self.per_page)  # Ceiling division
    
    @property
    def count(self) -> int:
        """Total de itens"""
        return self._count
    
    def get_elided_page_range(self, near_by: int = 2) -> range:
        """Retorna páginas com elipsamento"""
        if self.num_pages <= 7 + (near_by * 2):
            return range(1, self.num_pages + 1)
        
        # Páginas iniciais sempre mostradas
        result = list(range(1, near_by + 2))
        
        # Páginas do meio
        middle_start = max(near_by + 2, self.num_pages - near_by - 1)
        middle_end = min(self.num_pages - near_by, self.num_pages + 1)
        
        if middle_start > near_by + 3:
            result.append('...')
        
        result.extend(range(middle_start, middle_end))
        
        if middle_end < self.num_pages - near_by - 1:
            result.append('...')
        
        # Páginas finais
        result.extend(range(self.num_pages - near_by, self.num_pages + 1))
        
        return result


class Page:
    """Uma página específica"""
    
    def __init__(self, object_list: List[Any], number: int, paginator: Paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator
    
    def __iter__(self):
        return iter(self.object_list)
    
    def __len__(self) -> int:
        return len(self.object_list)
    
    @property
    def has_next(self) -> bool:
        return self.number < self.paginator.num_pages
    
    @property
    def has_previous(self) -> bool:
        return self.number > 1
    
    @property
    def has_other_pages(self) -> bool:
        return self.has_next or self.has_previous
    
    @property
    def next_page_number(self) -> Optional[int]:
        if self.has_next:
            return self.number + 1
        return None
    
    @property
    def previous_page_number(self) -> Optional[int]:
        if self.has_previous:
            return self.number - 1
        return None
    
    def start_index(self) -> int:
        """Índice do primeiro item na página"""
        return (self.number - 1) * self.paginator.per_page + 1
    
    def end_index(self) -> int:
        """Índice do último item na página"""
        return min(self.start_index() + self.paginator.per_page - 1, self.paginator.count)


# Função de conveniência
def paginate(object_list: List[Any], per_page: int, page: int = 1) -> Page:
    """Pagina uma lista de objetos"""
    paginator = Paginator(object_list, per_page)
    return paginator.page(page)
