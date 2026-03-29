#!/usr/bin/env python3
"""
Script para integrar cache de OSMnx em main.py
Modifica load_base_graph() para usar cache antes de reconstituir
"""

import re

# Lê o arquivo graph_builder.py
with open("graph/graph_builder.py", "r", encoding="utf-8") as f:
    content = f.read()

# Padrão a ser substituído (load_base_graph atual)
old_pattern = r'''    def load_base_graph\(self\):
        """Carrega grafo de ruas usando OSMnx\."""
        print\(f"Carregando grafo de \{self\.location\}\.\.\.\"\)\
        try:
            self\.base_graph = ox\.graph_from_place\(
                self\.location, network_type="drive", simplify=True
            \)
            print\(
                f"✓ Grafo carregado: \{len\(self\.base_graph\.nodes\)\} nós, \{len\(self\.base_graph\.edges\)\} arestas"
            \)
            return self\.base_graph
        except Exception as e:
            print\(f"✗ Erro ao carregar grafo: \{e\}"\)
            return None'''

# Novo código com cache
new_code = '''    def load_base_graph(self):
        """Carrega grafo de ruas usando OSMnx (com cache)."""
        # Tenta carregar de cache primeiro
        try:
            from graph.graph_cache_utils import load_base_graph_cache, save_base_graph_cache
            cached = load_base_graph_cache()
            if cached is not None:
                self.base_graph = cached
                return self.base_graph
        except Exception:
            pass
        
        # Se nao tiver cache, carrega do OSMnx
        print(f"Carregando grafo de {self.location}...")
        try:
            self.base_graph = ox.graph_from_place(
                self.location, network_type="drive", simplify=True
            )
            print(
                f"[OK] Grafo carregado: {len(self.base_graph.nodes)} nós, {len(self.base_graph.edges)} arestas"
            )
            # Salva em cache para próximas vezes
            try:
                from graph.graph_cache_utils import save_base_graph_cache
                save_base_graph_cache(self.base_graph)
            except Exception:
                pass
            return self.base_graph
        except Exception as e:
            print(f"[ERR] Erro ao carregar grafo: {e}")
            return None'''

# Faz o replace simples (procura a função exatamente)
if "def load_base_graph(self):" in content:
    # Extrai linha por linha e reconstrói
    lines = content.split('\n')
    new_lines = []
    skip_until_next_def = False
    
    for i, line in enumerate(lines):
        if 'def load_base_graph(self):' in line:
            skip_until_next_def = True
            new_lines.extend(new_code.split('\n'))
            continue
        
        if skip_until_next_def:
            if line.strip().startswith('def ') and 'load_base_graph' not in line:
                skip_until_next_def = False
                new_lines.append(line)
            elif not line.strip().startswith('def '):
                continue
        else:
            new_lines.append(line)
    
    # Escreve de volta
    with open("graph/graph_builder.py", "w", encoding="utf-8") as f:
        f.write('\n'.join(new_lines))
    
    print("[OK] graph_builder.py atualizado com cache de OSMnx")
else:
    print("[ERR] Nao foi possivel localizar load_base_graph()")
