"""
Módulo de Templates do Velox Framework

Sistema de templates com suporte a:
- Variáveis {{ variavel }}
- Condicionais {% if %}
- Loops {% for %}
- Herança de templates (extends/block)
- Macros reutilizáveis
- Filtros avançados
- Includes

Exemplo de uso:
    engine = TemplateEngine('templates')
    html = engine.render('index.html', {'nome': 'João'})
"""

import re
import os
import html as _html_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, date

# Conjunto de builtins seguros para _eval_expr — sem eval() em dados de usuário
_SAFE_BUILTINS = {
    'True': True, 'False': False, 'None': None,
    'range': range, 'len': len, 'str': str, 'int': int,
    'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
    'abs': abs, 'round': round, 'min': min, 'max': max,
    'enumerate': enumerate, 'zip': zip, 'sorted': sorted,
    'reversed': reversed, 'bool': bool,
}


class TemplateEngine:
    """
    Motor de templates
    
    Exemplo de uso:
        engine = TemplateEngine('templates')
        html = engine.render('index.html', {'nome': 'João'})
    
    Filtros disponíveis:
        {{ name|upper }}                    -> JOÃO
        {{ name|lower }}                    -> joão
        {{ name|title }}                    -> João
        {{ name|truncate:10 }}              -> João (10 chars)
        {{ date|date:"%d/%m/%Y" }}          -> 25/03/2026
        {{ html|safe }}                     -> Renderiza HTML
        {{ text|striptags }}                -> Remove tags HTML
        {{ price|currency:"R$" }}           -> R$ 10,00
        {{ items|join:", " }}               -> item1, item2
        {{ text|default:"N/A" }}            -> valor ou padrão
        {{ number|format:"%.2f" }}          -> 10.50
        {{ list|length }}                   -> tamanho
        {{ list|first }}                    -> primeiro item
        {{ list|last }}                    -> último item
    """
    
    def __init__(self, template_folder='templates'):
        self.template_folder = Path(template_folder)
        self._cache = {}
        self.filters = self._default_filters()
        self.macros = {}
        self._current_context = {}
    
    def _default_filters(self):
        """Filtros padrão disponíveis nos templates"""
        return {
            # Básicos
            'upper': lambda x: str(x).upper() if x else '',
            'lower': lambda x: str(x).lower() if x else '',
            'title': lambda x: str(x).title() if x else '',
            'trim': lambda x: str(x).strip() if x else '',
            'strip': lambda x: str(x).strip() if x else '',
            'length': lambda x: len(x) if x else 0,
            'count': lambda x: len(x) if x else 0,
            'first': lambda x: x[0] if (x and len(x) > 0) else '',
            'last': lambda x: x[-1] if (x and len(x) > 0) else '',
            
            # String
            'join': lambda x, sep=',': sep.join(x) if isinstance(x, (list, tuple)) else str(x),
            'split': lambda x, sep=',': str(x).split(sep),
            'replace': lambda x, old='', new='': str(x).replace(old, new),
            'truncate': lambda x, length=50: str(x)[:int(length)] + ('...' if len(str(x)) > int(length) else ''),
            'truncatewords': lambda x, words=10: ' '.join(str(x).split()[:int(words)]) + ('...' if len(str(x).split()) > int(words) else ''),
            'wordcount': lambda x: len(str(x).split()),
            'capfirst': lambda x: str(x)[0].upper() + str(x)[1:] if x else '',
            'center': lambda x, width=80: str(x).center(int(width)),
            'ljust': lambda x, width=80: str(x).ljust(int(width)),
            'rjust': lambda x, width=80: str(x).rjust(int(width)),
            
            # Número
            'int': lambda x: int(x) if x else 0,
            'float': lambda x: float(x) if x else 0.0,
            'format': lambda x, fmt='%.2f': fmt % float(x) if x else '0.00',
            'currency': lambda x, symbol='R$': f"{symbol} {float(x):,.2f}".replace('.', ',').replace(',', '.', 1) if x else f"{symbol} 0,00",
            'percent': lambda x, decimals=1: f"{float(x):.{int(decimals)}%}" if x else '0%',
            
            # Data/Hora
            'date': lambda x, fmt='%d/%m/%Y': (
                x.strftime(fmt) if isinstance(x, (datetime, date)) 
                else datetime.strptime(str(x), '%Y-%m-%d').strftime(fmt) if isinstance(x, str) and '-' in str(x)[:10]
                else str(x)
            ),
            'time': lambda x, fmt='%H:%M:%S': (
                x.strftime(fmt) if isinstance(x, datetime)
                else str(x)
            ),
            'datetime': lambda x, fmt='%d/%m/%Y %H:%M:%S': (
                x.strftime(fmt) if isinstance(x, datetime)
                else str(x)
            ),
            
            # HTML
            'safe': lambda x: x if hasattr(x, '__html__') else str(x),
            'striptags': lambda x: re.sub(r'<[^>]+>', '', str(x)),
            'linebreaks': lambda x: str(x).replace('\n', '<br>'),
            'linebreaksbr': lambda x: str(x).replace('\n', '<br>'),
            
            # Booleanos
            'yesno': lambda x, yes='yes', no='no', maybe='maybe': yes if x else (maybe if x is None else no),
            'boolean': lambda x: bool(x),
            'default': lambda x, default='': x if x else default,
            'default_if_none': lambda x, default='': x if x is not None else default,
            
            # Listas
            'random': lambda x: x[int(len(x) * __import__('random').random())] if x and len(x) > 0 else None,
            'reverse': lambda x: list(reversed(x)) if x else [],
            'sort': lambda x, reverse=False: sorted(x, reverse=reverse) if x else [],
            'slice': lambda x, start=0, end=None: x[int(start):int(end) if end else None],
            'unique': lambda x: list(dict.fromkeys(x)) if x else [],
            'joinattr': lambda x, attr, sep=', ': sep.join(str(getattr(i, attr)) for i in x) if x else '',
            
            # Utils
            'add': lambda x, y: int(x) + int(y),
            'subtract': lambda x, y: int(x) - int(y),
            'multiply': lambda x, y: int(x) * int(y),
            'divide': lambda x, y: int(x) / int(y) if int(y) != 0 else 0,
            'mod': lambda x, y: int(x) % int(y),
            'abs': lambda x: abs(float(x)) if x else 0,
            'round': lambda x, decimals=0: round(float(x), int(decimals)),
            
            # URL
            'urlencode': lambda x: __import__('urllib.parse').quote(str(x)),
            'urlize': lambda x: re.sub(r'(http[s]?://[^\s]+)', r'<a href="\1">\1</a>', str(x)),
        }
    
    def add_filter(self, name: str, func: Callable):
        """Adiciona um filtro personalizado"""
        self.filters[name] = func
    
    def add_filters(self, filters: Dict[str, Callable]):
        """Adiciona múltiplos filtros de uma vez"""
        self.filters.update(filters)
    
    def render(self, template_name: str, context: Dict = None) -> str:
        """Renderiza um template"""
        if context is None:
            context = {}
        
        self._current_context = context.copy()
        
        # Adicionar filtros ao contexto
        context['_filters'] = self.filters
        
        template_path = self.template_folder / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{template_name}' não encontrado em {template_path}")
        
        # Ler template (com cache opcional)
        if os.getenv('TEMPLATE_CACHE', 'true').lower() == 'true':
            cache_key = f"template:{template_name}"
            from .cache import template_cache
            cached = template_cache.get(template_name)
            if cached:
                content = cached
            else:
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                template_cache.set(template_name, content)
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Processar template
        return self._render_content(content, context)
    
    def _render_content(self, content: str, context: Dict) -> str:
        """Processa o conteúdo do template"""
        # Processar macros primeiro
        content = self._process_macros(content, context)
        
        # Processar herança
        content = self._process_extends(content, context)
        
        # Processar includes
        content = self._process_includes(content, context)
        
        # Processar blocos
        content = self._process_blocks(content, context)
        
        # Processar condicionais
        content = self._process_conditionals(content, context)
        
        # Processar loops
        content = self._process_loops(content, context)
        
        # Processar variáveis
        content = self._process_variables(content, context)
        
        # Processar filtros
        content = self._process_filter_syntax(content, context)
        
        return content
    
    def _process_macros(self, content: str, context: Dict) -> str:
        """Processa definição de macros"""
        macro_pattern = r'\{%\s*macro\s+(\w+)(?:\(([^)]*)\))?\s*%\}(.*?)\{%\s*endmacro\s*%\}'
        
        def save_macro(match):
            name = match.group(1)
            params = [p.strip() for p in match.group(2).split(',')] if match.group(2) else []
            body = match.group(3)
            self.macros[name] = {'params': params, 'body': body}
            return ''
        
        content = re.sub(macro_pattern, save_macro, content, flags=re.DOTALL)
        
        # Processar chamadas de macros
        call_pattern = r'\{%\s*call\s+(\w+)(?:\(([^)]*)\))?\s*%\}'
        
        def execute_macro(match):
            name = match.group(1)
            args = [a.strip() for a in match.group(2).split(',')] if match.group(2) else []
            
            if name not in self.macros:
                return f'<!-- Macro "{name}" não encontrado -->'
            
            macro = self.macros[name]
            macro_context = dict(context)
            
            # Bind argumentos aos parâmetros
            for i, param in enumerate(macro['params']):
                if i < len(args):
                    macro_context[param] = self._eval_expr(args[i], context)
            
            return self._render_content(macro['body'], macro_context)
        
        content = re.sub(call_pattern, execute_macro, content)
        
        return content
    
    def _process_extends(self, content: str, context: Dict) -> str:
        """Processa herança de templates"""
        extends_pattern = r'\{%\s*extends\s+["\']([^"\']+)["\']\s*%\}'
        match = re.search(extends_pattern, content)
        
        if match:
            parent_template = match.group(1)
            parent_path = self.template_folder / parent_template
            
            if not parent_path.exists():
                raise FileNotFoundError(f"Template pai '{parent_template}' não encontrado")
            
            with open(parent_path, 'r', encoding='utf-8') as f:
                parent_content = f.read()
            
            # Extrair blocos do template filho
            block_pattern = r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}'
            child_blocks = {}
            for m in re.finditer(block_pattern, content, re.DOTALL):
                block_name = m.group(1)
                block_content = m.group(2).strip()
                child_blocks[block_name] = block_content
            
            # Substituir blocos no template pai
            for block_name, block_content in child_blocks.items():
                # Padrão para bloco com conteúdo padrão no pai
                parent_block_pattern = f'\\{{%\\s*block\\s+{block_name}\\s*%\\}}(.*?)\\{{%\\s*endblock\\s*%\\}}'
                parent_match = re.search(parent_block_pattern, parent_content, re.DOTALL)
                if parent_match:
                    parent_content = parent_content.replace(
                        parent_match.group(0),
                        block_content
                    )
            
            # Remover tags extends e blocks do conteúdo
            content = re.sub(extends_pattern, '', content)
            content = re.sub(block_pattern, '', content, flags=re.DOTALL)
            
            # Processar herança recursivamente
            return self._render_content(parent_content, context)
        
        return content
    
    def _process_includes(self, content: str, context: Dict) -> str:
        """Processa includes de templates"""
        include_pattern = r'\{%\s*include\s+["\']([^"\']+)(?:\s+with\s+([^"\']+))?["\']\s*%\}'
        
        def replace_include(match):
            include_name = match.group(1)
            include_context = dict(context)
            
            # Permite passar contexto adicional
            if match.group(2):
                extra_context = self._eval_expr(match.group(2), context)
                if isinstance(extra_context, dict):
                    include_context.update(extra_context)
            
            try:
                return self.render(include_name, include_context)
            except Exception as e:
                return f"<!-- Erro ao incluir {include_name}: {e} -->"
        
        return re.sub(include_pattern, replace_include, content)
    
    def _process_blocks(self, content: str, context: Dict) -> str:
        """Processa blocos"""
        # Remove apenas as tags de block, o conteúdo já foi processado
        block_pattern = r'\{%\s*block\s+(\w+)\s*%\}|\{%\s*endblock\s*%\}'
        return re.sub(block_pattern, '', content)
    
    def _process_conditionals(self, content: str, context: Dict) -> str:
        """Processa condicionais {% if %}"""
        if_pattern = r'\{%\s*if\s+(.+?)\s*%\}'
        elif_pattern = r'\{%\s*elif\s+(.+?)\s*%\}'
        else_pattern = r'\{%\s*else\s*%\}'
        endif_pattern = r'\{%\s*endif\s*%\}'
        
        def evaluate_condition(condition: str, ctx: Dict) -> bool:
            """Avalia uma condição de forma segura sem eval()"""
            condition = condition.strip()

            # not expr
            if condition.startswith('not '):
                return not evaluate_condition(condition[4:].strip(), ctx)

            # expr and expr
            if ' and ' in condition:
                parts = condition.split(' and ', 1)
                return evaluate_condition(parts[0], ctx) and evaluate_condition(parts[1], ctx)

            # expr or expr
            if ' or ' in condition:
                parts = condition.split(' or ', 1)
                return evaluate_condition(parts[0], ctx) or evaluate_condition(parts[1], ctx)

            # comparações: ==, !=, >=, <=, >, <, in, not in
            for op in ('!=', '==', '>=', '<=', '>', '<', ' not in ', ' in '):
                if op in condition:
                    left, right = condition.split(op, 1)
                    lv = self._eval_expr(left.strip(), ctx)
                    rv = self._eval_expr(right.strip(), ctx)
                    if op == '==':      return lv == rv
                    if op == '!=':      return lv != rv
                    if op == '>=':      return lv >= rv
                    if op == '<=':      return lv <= rv
                    if op == '>':       return lv > rv
                    if op == '<':       return lv < rv
                    if op == ' in ':    return lv in rv if rv else False
                    if op == ' not in ':return lv not in rv if rv else True

            # valor simples — truthy
            val = self._eval_expr(condition, ctx)
            return bool(val)
        
        # Simplificado: processar if/else básico
        parts = re.split(r'(\{%\s*(if|elif|else|endif)[^%]*%\})', content)
        
        result = []
        i = 0
        skip_depth = 0
        
        while i < len(parts):
            part = parts[i]
            
            if re.match(r'\{%\s*if\s+', part):
                condition = re.search(r'\{%\s*if\s+(.+?)\s*%\}', part)
                if condition:
                    if skip_depth == 0:
                        if evaluate_condition(condition.group(1), context):
                            skip_depth = 1
                            i += 1
                            continue
                        else:
                            skip_depth = -1
                    else:
                        skip_depth += (-1 if skip_depth > 0 else 1)
            elif re.match(r'\{%\s*elif\s+', part):
                condition = re.search(r'\{%\s*elif\s+(.+?)\s*%\}', part)
                if condition:
                    if skip_depth == -1:
                        if evaluate_condition(condition.group(1), context):
                            skip_depth = 0
            elif re.match(r'\{%\s*else\s*%\}', part):
                if skip_depth == -1:
                    skip_depth = 0
            elif re.match(r'\{%\s*endif\s*%\}', part):
                if skip_depth != 0:
                    skip_depth += (-1 if skip_depth > 0 else 1)
                    if skip_depth == 0:
                        skip_depth = 0
            else:
                if skip_depth == 0:
                    result.append(part)
            
            i += 1
        
        return ''.join(result)
    
    def _process_loops(self, content: str, context: Dict) -> str:
        """Processa loops {% for %}"""
        for_pattern = r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}'
        endfor_pattern = r'\{%\s*endfor\s*%\}'
        empty_pattern = r'\{%\s*empty\s*%\}(.*?)(?=\{%\s*endfor)'
        
        def replace_for(match):
            var_name = match.group(1)
            iterable_expr = match.group(2)
            
            # Encontrar o corpo do loop
            start = match.end()
            rest = content[start:]
            
            # Encontrar endfor
            endfor_match = re.search(r'\{%\s*endfor\s*%\}', rest)
            if not endfor_match:
                return match.group(0)
            
            body = rest[:endfor_match.start()]
            
            # Verificar bloco empty
            empty_match = re.search(r'\{%\s*empty\s*%\}(.*)', rest[:endfor_match.start()], re.DOTALL)
            empty_body = ''
            if empty_match:
                body = rest[:empty_match.start()]
                empty_body = empty_match.group(1)
            
            # Avaliar o iterável
            try:
                items = self._eval_expr(iterable_expr, context)
                
                if not items or (isinstance(items, (list, tuple, dict, range)) and len(items) == 0):
                    return empty_body
                
                result = []
                
                if isinstance(items, dict):
                    keys = list(items.keys())
                    for idx, k in enumerate(keys):
                        v = items[k]
                        ctx = dict(context)
                        ctx[var_name] = v
                        ctx[f'{var_name}_key'] = k
                        ctx[f'{var_name}_index'] = idx
                        ctx[f'{var_name}_first'] = (idx == 0)
                        ctx[f'{var_name}_last'] = (idx == len(keys) - 1)
                        ctx[f'{var_name}_length'] = len(keys)
                        ctx[f'{var_name}_revindex'] = len(keys) - idx
                        result.append(self._render_content(body, ctx))
                else:
                    for idx, item in enumerate(items):
                        ctx = dict(context)
                        ctx[var_name] = item
                        ctx[f'{var_name}_index'] = idx
                        ctx[f'{var_name}_first'] = (idx == 0)
                        ctx[f'{var_name}_last'] = (idx == len(items) - 1)
                        ctx[f'{var_name}_length'] = len(items)
                        ctx[f'{var_name}_revindex'] = len(items) - idx
                        result.append(self._render_content(body, ctx))
                
                return ''.join(result)
            except Exception as e:
                return f'<!-- Erro no loop: {e} -->' + empty_body
        
        # Processar todos os loops
        result = content
        while True:
            match = re.search(for_pattern, result)
            if not match:
                break
            
            start = match.start()
            rest = result[match.end():]
            endfor_match = re.search(r'\{%\s*endfor\s*%\}', rest)
            if not endfor_match:
                break
            
            body = rest[:endfor_match.start()]
            
            # Verificar bloco empty
            empty_match = re.search(r'\{%\s*empty\s*%\}(.*)', body, re.DOTALL)
            empty_body = ''
            if empty_match:
                body = body[:empty_match.start()]
                empty_body = empty_match.group(1)
            
            # Avaliar loop
            var_name = match.group(1)
            iterable_expr = match.group(2)
            
            try:
                items = self._eval_expr(iterable_expr, context)
                
                if not items or (isinstance(items, (list, tuple, dict, range)) and len(items) == 0):
                    result = result[:start] + empty_body + result[start + len(match.group(0)) + endfor_match.end():]
                    continue
                
                loop_result = []
                
                if isinstance(items, dict):
                    keys = list(items.keys())
                    for idx, k in enumerate(keys):
                        v = items[k]
                        ctx = dict(context)
                        ctx[var_name] = v
                        ctx[f'{var_name}_key'] = k
                        ctx[f'{var_name}_index'] = idx
                        ctx[f'{var_name}_first'] = (idx == 0)
                        ctx[f'{var_name}_last'] = (idx == len(keys) - 1)
                        ctx[f'{var_name}_length'] = len(keys)
                        loop_result.append(self._render_content(body, ctx))
                else:
                    for idx, item in enumerate(items):
                        ctx = dict(context)
                        ctx[var_name] = item
                        ctx[f'{var_name}_index'] = idx
                        ctx[f'{var_name}_first'] = (idx == 0)
                        ctx[f'{var_name}_last'] = (idx == len(items) - 1)
                        ctx[f'{var_name}_length'] = len(items)
                        loop_result.append(self._render_content(body, ctx))
                
                end_pos = len(match.group(0)) + endfor_match.end()
                result = result[:start] + ''.join(loop_result) + result[start + end_pos:]
            except Exception as e:
                result = result[:start] + f'<!-- Erro no loop: {e} -->' + result[start + len(match.group(0)) + endfor_match.end():]
        
        # Remover tags endfor
        result = re.sub(endfor_pattern, '', result)
        
        return result
    
    def _escape(self, value: Any) -> str:
        """Escapa HTML por padrão para prevenir XSS. Use o filtro |safe para desativar."""
        if value is None:
            return ''
        return _html_module.escape(str(value))

    def _eval_expr(self, expr: str, context: Dict) -> Any:
        """
        Avalia uma expressão de template de forma segura — sem eval() em dados externos.
        Suporta: variáveis simples, acesso a atributos (a.b), índices (a.0),
        literais string/int/bool, filtros com pipe (|), e operações básicas.
        """
        expr = expr.strip()
        if not expr:
            return None

        # Literal string
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Literal inteiro/float
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Booleanos e None
        if expr == 'True':  return True
        if expr == 'False': return False
        if expr == 'None':  return None

        # Filtros com pipe
        if '|' in expr:
            parts = expr.split('|', 1)
            value = self._eval_expr(parts[0].strip(), context)
            for fpart in parts[1].split('|'):
                fpart = fpart.strip()
                if ':' in fpart:
                    fname, farg = fpart.split(':', 1)
                    fname = fname.strip()
                    farg  = farg.strip().strip('"').strip("'")
                    if fname in self.filters:
                        try:
                            value = self.filters[fname](value, farg)
                        except Exception:
                            pass
                elif fpart in self.filters:
                    try:
                        value = self.filters[fpart](value)
                    except Exception:
                        pass
            return value

        # Acesso a atributos/índices com ponto: user.name, items.0
        if '.' in expr:
            parts = expr.split('.')
            value = context.get(parts[0])
            for part in parts[1:]:
                if value is None:
                    return None
                try:
                    idx = int(part)
                    value = value[idx]
                except (ValueError, TypeError, IndexError):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = getattr(value, part, None)
            return value

        # Variável simples do contexto
        return context.get(expr)
    
    def _process_variables(self, content: str, context: Dict) -> str:
        """Processa variáveis {{ variavel }} com escape HTML automático."""
        var_pattern = r'\{\{\s*(.+?)\s*\}\}'

        def replace_var(match):
            expr = match.group(1).strip()

            # Detectar filtro |safe em qualquer posição da cadeia de filtros
            is_safe = bool(re.search(r'(?:^|\|)\s*safe\s*(?:\||$)', expr))
            if is_safe:
                # Remove todas as ocorrências de |safe (com espaços opcionais)
                expr = re.sub(r'\|\s*safe\s*', '|', expr).strip('|').strip()

            value = self._eval_expr(expr, context)

            if value is None:
                return ''
            if is_safe:
                return str(value)
            return self._escape(value)

        return re.sub(var_pattern, replace_var, content)
    
    def _process_filter_syntax(self, content: str, context: Dict) -> str:
        """Processa sintaxe de filtros |filter_name"""
        # Já processado em _process_variables
        return content


def render_template(template_name: str, context: Dict = None, template_folder: str = 'templates') -> str:
    """Função de conveniência para renderizar templates"""
    engine = TemplateEngine(template_folder)
    return engine.render(template_name, context)
