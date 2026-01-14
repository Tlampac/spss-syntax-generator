"""
SPSS Syntax Generator
Automatické generování SPSS syntax z dat a dotazníku
"""

import pyreadstat
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import docx


class SPSSSyntaxGenerator:
    """Generátor SPSS syntax z exportovaných dat a dotazníku"""
    
    def __init__(self, data_path: str, questionnaire_path: str):
        self.data_path = data_path
        self.questionnaire_path = questionnaire_path
        self.df = None
        self.meta = None
        self.questionnaire = {}
        self.syntax_parts = []
        
    def load_data(self):
        """Načtení SPSS dat"""
        print("📂 Načítám SPSS data...")
        self.df, self.meta = pyreadstat.read_sav(self.data_path)
        print(f"   ✓ Načteno {len(self.df)} respondentů, {len(self.df.columns)} proměnných")
        
    def load_questionnaire(self):
        """Načtení dotazníku z DOCX"""
        print("📋 Načítám dotazník...")
        doc = docx.Document(self.questionnaire_path)
        
        current_question = None
        current_options = []
        collecting_options = False
        
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
                
            # Detekce otázky (začíná kódem typu R1., S1., Z1a. atd.)
            if re.match(r'^[A-Z]\d+[a-z]?\.\s+', text):
                # Uložit předchozí otázku
                if current_question:
                    current_question['options'] = current_options
                    self.questionnaire[current_question['code']] = current_question
                
                # Nová otázka
                match = re.match(r'^([A-Z]\d+[a-z]?)\.?\s+(.+)', text)
                if match:
                    code = match.group(1)
                    question_text = match.group(2)
                    current_question = {
                        'code': code,
                        'text': question_text,
                        'options': [],
                        'type': None
                    }
                    current_options = []
                    collecting_options = True
                    
            # Detekce typu otázky
            elif 'Vyberte typ otázky::' in text:
                if current_question:
                    qtype = text.replace('Vyberte typ otázky::', '').strip()
                    current_question['type'] = qtype
                collecting_options = False
                    
            # Detekce možností odpovědi (odrážky nebo samostatné řádky mezi otázkou a typem)
            elif current_question:
                # Přeskočit meta informace
                if any(skip in text for skip in ['Nastavení', 'Povinná', 'Vyberte typ', 'Zvolených minimálně']):
                    collecting_options = False
                    continue
                    
                # Collecting options mezi otázkou a "Vyberte typ otázky"
                if collecting_options:
                    if text.startswith('-'):
                        option = text.lstrip('- ').strip()
                        if option:
                            current_options.append(option)
                    else:
                        # Samostatný řádek jako option (pro Z3 apod.)
                        # Ale ne další otázka nebo meta info
                        if not re.match(r'^[A-Z]\d+[a-z]?\.\s+', text) and len(text) < 100:
                            current_options.append(text)
                        
        # Uložit poslední otázku
        if current_question:
            current_question['options'] = current_options
            self.questionnaire[current_question['code']] = current_question
            
        print(f"   ✓ Načteno {len(self.questionnaire)} otázek")
        
    def identify_variable_patterns(self) -> Dict[str, List[str]]:
        """Identifikace skupin proměnných podle vzorců"""
        patterns = {
            'batteries': {},      # QS1__1, QS1__2 -> baterie otázek
            'mr_dichotomous': {}, # QZ3__1, QZ3__2 -> multiple response dichotomické
            'mr_categorical': {}, # QZ1a__0_jina -> multiple response kategoriální
            'single_open': [],    # QK1, QB1 -> jednopólové otevřené (stringy)
            'filtered_batteries': {}, # QA6__A2_1 -> filtrované baterie (podle jiné otázky)
            'filtered_mr_batteries': {}, # QB2__A2_1column1 -> filtrované MR baterie
            'standard': []        # QR1, QR3 -> standardní otázky
        }
        
        for var_name in self.df.columns:
            # Filtrované MR baterie - pattern: Q{code}__{filter}_{num}column{col}
            match = re.match(r'^Q([A-Z]\d+[a-z]?)__([A-Z]\d+[a-z]?)_(\d+)column(\d+)$', var_name)
            if match:
                code = match.group(1)
                filter_q = match.group(2)
                if code not in patterns['filtered_mr_batteries']:
                    patterns['filtered_mr_batteries'][code] = {'filter': filter_q, 'vars': []}
                patterns['filtered_mr_batteries'][code]['vars'].append(var_name)
                continue
            
            # Filtrované baterie - pattern: Q{code}__{filter}_{num}
            match = re.match(r'^Q([A-Z]\d+[a-z]?)__([A-Z]\d+[a-z]?)_(\d+)$', var_name)
            if match:
                code = match.group(1)
                filter_q = match.group(2)
                if code not in patterns['filtered_batteries']:
                    patterns['filtered_batteries'][code] = {'filter': filter_q, 'vars': []}
                patterns['filtered_batteries'][code]['vars'].append(var_name)
                continue
            
            # Baterie otázek - pattern: Q{code}__{number}
            match = re.match(r'^Q([A-Z]\d+[a-z]?)__(\d+)$', var_name)
            if match:
                code = match.group(1)
                item_num = match.group(2)
                if code not in patterns['batteries']:
                    patterns['batteries'][code] = []
                patterns['batteries'][code].append(var_name)
                continue
                
            # MR kategoriální - pattern: Q{code}__{number}_{suffix}
            match = re.match(r'^Q([A-Z]\d+[a-z]?)__\d+_\w+$', var_name)
            if match:
                code = match.group(1)
                if code not in patterns['mr_categorical']:
                    patterns['mr_categorical'][code] = []
                patterns['mr_categorical'][code].append(var_name)
                continue
                
            # Standardní otázky - pattern: Q{code}
            match = re.match(r'^Q([A-Z]\d+[a-z]?)$', var_name)
            if match:
                # Kontrola zda je to string (otevřená otázka) nebo číselná
                if self.df[var_name].dtype == 'object':
                    # String = jednopólová otevřená otázka
                    patterns['single_open'].append(var_name)
                else:
                    # Číselná = standardní otázka
                    patterns['standard'].append(var_name)
                
        return patterns
        
    def extract_item_text(self, full_label: str) -> str:
        """Extrahuje text položky z plného labelu"""
        # Pattern: "Otázka\n|Položka" nebo "Otázka\n Položka"
        if '|' in full_label:
            return full_label.split('|')[-1].strip()
        elif '\n' in full_label:
            parts = full_label.split('\n')
            # Vezme poslední neprázdnou část
            for part in reversed(parts):
                part = part.strip()
                if part and not part.startswith('Q'):
                    return part
        return full_label
        
    def generate_syntax(self) -> str:
        """Hlavní metoda pro generování syntax"""
        print("\n🔧 Generuję SPSS syntax...")
        
        self.syntax_parts = []
        
        # 1. Filtr na dokončené respondenty
        self._generate_filter()
        
        # 2. Identifikace vzorců
        patterns = self.identify_variable_patterns()
        
        # 3. Baterie otázek
        self._generate_batteries(patterns['batteries'])
        
        # 4. MR dichotomické
        self._generate_mr_dichotomous(patterns['batteries'])
        
        # 5. Filtrované baterie (A6)
        self._generate_filtered_batteries(patterns['filtered_batteries'])
        
        # 6. Filtrované MR baterie (B2)
        self._generate_filtered_mr_batteries(patterns['filtered_mr_batteries'])
        
        # 7. Jednopólové otevřené (K1, B1)
        self._generate_single_open(patterns['single_open'])
        
        # 8. MR kategoriální
        self._generate_mr_categorical(patterns['mr_categorical'])
        
        # Spojení všech částí
        syntax = '\n\n'.join(self.syntax_parts)
        
        print("   ✓ Syntax vygenerována")
        return syntax
        
    def _generate_filter(self):
        """Generuje filtr na dokončené respondenty"""
        section = """* OMEZENÍ DAT NA RESPONDENTY, KTEŘÍ DOKONČILI DOTAZNÍK.
SELECT IF resstatus = 2.
EXECUTE.
FREQUENCIES resstatus."""
        self.syntax_parts.append(section)
        
    def _generate_batteries(self, batteries: Dict[str, List[str]]):
        """Generuje VAR LAB pro baterie otázek"""
        if not batteries:
            return
            
        section = ["* ÚPRAVA LABELŮ PRO BATERIE OTÁZEK - v tabulkách zobrazí jen text položky."]
        
        for code, variables in sorted(batteries.items()):
            # Najít otázku v dotazníku
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
                
            # Kontrola zda je to baterie (má více položek a je typu baterie)
            if q_info.get('type') and 'BATERIE' in q_info['type']:
                section.append(f"\n* {code} - {q_info['text'][:60]}...")
                
                for i, var_name in enumerate(sorted(variables)):
                    # Získat text položky z původního labelu
                    orig_label = self.meta.column_names_to_labels.get(var_name, '')
                    item_text = self.extract_item_text(orig_label)
                    
                    # Pokud máme options v dotazníku, použijeme je
                    if i < len(q_info.get('options', [])):
                        item_text = q_info['options'][i]
                    
                    section.append(f'VAR LAB {var_name} "{item_text}".')
                    
        if len(section) > 1:
            section.append("EXECUTE.")
            self.syntax_parts.append('\n'.join(section))
        
    def _generate_mr_dichotomous(self, batteries: Dict[str, List[str]]):
        """Generuje MR sety pro dichotomické otázky (typ VÍCE MOŽNÝCH ODPOVĚDÍ)"""
        section = ["* PŘÍPRAVA MULTIPLE RESPONSE SETŮ - DICHOTOMICKÉ OTÁZKY."]
        mrsets_commands = []
        
        for code, variables in sorted(batteries.items()):
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
            
            # Přeskočit otázky, které mají filtrované verze (např. A3 má QA3__1 i QA3__A2_1)
            # Pokud existují proměnné s pattern Q{code}__{filter}_{num}, tak tato otázka
            # se zpracovává jako filtrovaná baterie, ne jako MR dichotomická
            has_filtered_version = any(
                col for col in self.df.columns 
                if re.match(f'^Q{code}__[A-Z]\\d+[a-z]?_\\d+', col)
            )
            
            if has_filtered_version:
                # Tato otázka má filtrovanou verzi, zpracuje se jinde
                continue
                
            # Kontrola zda je to MR dichotomická otázka
            # Buď podle typu v dotazníku, nebo podle hodnot v datech (0,1,2 = dichotomická MR)
            is_mr_dichotomous = False
            
            if q_info.get('type') and 'VÍCE MOŽNÝCH ODPOVĚDÍ' in q_info['type']:
                is_mr_dichotomous = True
            else:
                # Kontrola hodnot v první proměnné
                if variables:
                    first_var = variables[0]
                    unique_vals = set(self.df[first_var].dropna().unique())
                    # Pokud obsahuje hodnoty typické pro MR (0,1,2 nebo jejich kombinaci)
                    if unique_vals.issubset({0, 1, 2, 0.0, 1.0, 2.0}):
                        is_mr_dichotomous = True
            
            if is_mr_dichotomous:
                section.append(f"\n* {code} - {q_info['text'][:60]}...")
                section.append(f"* Úprava labelů na názvy jednotlivých položek.")
                
                # Variable labels
                sorted_vars = sorted(variables, key=lambda x: int(re.search(r'__(\d+)', x).group(1)) if re.search(r'__(\d+)', x) else 0)
                for i, var_name in enumerate(sorted_vars):
                    if i < len(q_info.get('options', [])):
                        option_text = q_info['options'][i]
                        section.append(f'VAR LAB {var_name} "{option_text}".')
                
                section.append("EXECUTE.")
                
                # MRSETS command
                sorted_vars = sorted(variables, key=lambda x: int(re.search(r'__(\d+)', x).group(1)) if re.search(r'__(\d+)', x) else 0)
                var_list = ' '.join(sorted_vars)
                mrset_name = f"${code.lower()}"
                mrsets_cmd = f"""
* Vytvoření MR setu pro {code}.
MRSETS
  /MDGROUP NAME={mrset_name} CATEGORYLABELS=VARLABELS 
  VARIABLES={var_list} VALUE=2
  /DISPLAY NAME=[{mrset_name}]."""
                mrsets_commands.append(mrsets_cmd)
        
        if len(section) > 1:
            self.syntax_parts.append('\n'.join(section))
            if mrsets_commands:
                self.syntax_parts.append('\n'.join(mrsets_commands))
                
    def _generate_mr_categorical(self, mr_categorical: Dict[str, List[str]]):
        """Generuje labely pro kategoriální otázky (otevřené s více poli) a MCGROUP pro nakódované verze"""
        if not mr_categorical:
            return
            
        section = ["* VARIABLE LABELS PRO OTEVŘENÉ OTÁZKY."]
        mrsets_commands = []
        
        # Nejdřív zpracovat otevřenky které MAJÍ stringové verze
        processed_codes = set()
        
        for code, variables in sorted(mr_categorical.items()):
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
            
            processed_codes.add(code)
                
            section.append(f"\n* {code} - {q_info['text'][:60]}...")
            
            # Zkontrolovat, jestli existují nakódované verze (např. QZ1a_1, QZ1a_2)
            # Pattern: Q{code}_1, Q{code}_2 (bez _jina, bez __)
            coded_vars = []
            for col in self.df.columns:
                # Hledám Q{code}_{číslo} bez dalších podtržítek
                if col.startswith(f'Q{code}_') and '__' not in col and '_jina' not in col:
                    # Extrahovat číslo za podtržítkem
                    suffix = col[len(f'Q{code}_'):]
                    if suffix.isdigit():
                        # Kontrola že je to numeric (nakódované)
                        if self.df[col].dtype in ['int64', 'float64']:
                            coded_vars.append(col)
            
            # Seřadit numericky
            coded_vars = sorted(coded_vars, key=lambda x: int(x.split('_')[-1]))
            
            # Variable labels pro stringové verze - celý text otázky
            full_text = q_info['text']
            for var_name in sorted(variables):
                section.append(f'VAR LAB {var_name} "{full_text}".')
            
            section.append("EXECUTE.")
            
            # Pokud existují nakódované verze, vytvořit MCGROUP
            if coded_vars:
                section.append(f"* Nakódované odpovědi pro {code}:")
                for var_name in coded_vars:
                    section.append(f'VAR LAB {var_name} "{full_text}".')
                section.append("EXECUTE.")
                
                # MRSETS command
                var_list = ' '.join(coded_vars)
                mrset_name = f"${code.lower()}"
                mrsets_cmd = f"""
* Vytvoření MR setu pro nakódované odpovědi {code}.
MRSETS
  /MCGROUP NAME={mrset_name} VARIABLES={var_list}
  /DISPLAY NAME=[{mrset_name}]."""
                mrsets_commands.append(mrsets_cmd)
        
        # Teď zpracovat otevřenky které NEMAJÍ stringové verze, ale MAJÍ nakódované
        # Projít všechny otázky v dotazníku typu OTEVŘENÁ OTÁZKA
        for q_code, q_info in self.questionnaire.items():
            if q_code in processed_codes:
                continue
                
            if not q_info.get('type'):
                continue
                
            if 'OTEVŘENÁ OTÁZKA' not in q_info['type']:
                continue
            
            # Hledat nakódované verze
            coded_vars = []
            for col in self.df.columns:
                if col.startswith(f'Q{q_code}_') and '__' not in col and '_jina' not in col:
                    suffix = col[len(f'Q{q_code}_'):]
                    if suffix.isdigit():
                        if self.df[col].dtype in ['int64', 'float64']:
                            coded_vars.append(col)
            
            if not coded_vars:
                continue
                
            # Seřadit numericky
            coded_vars = sorted(coded_vars, key=lambda x: int(x.split('_')[-1]))
            
            section.append(f"\n* {q_code} - {q_info['text'][:60]}...")
            section.append(f"* Nakódované odpovědi:")
            
            full_text = q_info['text']
            for var_name in coded_vars:
                section.append(f'VAR LAB {var_name} "{full_text}".')
            section.append("EXECUTE.")
            
            # MRSETS command
            var_list = ' '.join(coded_vars)
            mrset_name = f"${q_code.lower()}"
            mrsets_cmd = f"""
* Vytvoření MR setu pro nakódované odpovědi {q_code}.
MRSETS
  /MCGROUP NAME={mrset_name} VARIABLES={var_list}
  /DISPLAY NAME=[{mrset_name}]."""
            mrsets_commands.append(mrsets_cmd)
        
        if len(section) > 1:
            self.syntax_parts.append('\n'.join(section))
            if mrsets_commands:
                self.syntax_parts.append('\n'.join(mrsets_commands))
    
    def _generate_filtered_batteries(self, filtered_batteries: Dict[str, Dict]):
        """Generuje VAR LAB a MRSETS pro filtrované baterie (např. A6__A2_1)"""
        if not filtered_batteries:
            return
            
        section = ["* VARIABLE LABELS PRO FILTROVANÉ BATERIE."]
        mrsets_commands = []
        
        for code, info in sorted(filtered_batteries.items()):
            filter_q = info['filter']
            variables = info['vars']
            
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
            
            # Pro FILTRACE ODPOVĚDÍ použít options ze zdrojové otázky
            filter_q_info = self.questionnaire.get(filter_q)
            use_filter_options = False
            
            if q_info.get('type') and 'FILTRACE ODPOVĚDÍ' in q_info['type']:
                # Použít options z filter_q místo z aktuální otázky
                if filter_q_info and filter_q_info.get('options'):
                    use_filter_options = True
            
            # Získat názvy položek - buď z filter otázky, nebo z labelů proměnných
            filter_items = {}
            
            if use_filter_options:
                # Použít options z dotazníku filtrační otázky
                for i, option in enumerate(filter_q_info['options'], 1):
                    filter_items[i] = option
            else:
                # Jinak extrahovat z labelů proměnných
                filter_vars = [col for col in self.df.columns if col.startswith(f'Q{filter_q}__')]
                for fvar in filter_vars:
                    label = self.meta.column_names_to_labels.get(fvar, '')
                    if '\n' in label:
                        item_name = label.split('\n')[-1].strip()
                    elif '|' in label:
                        item_name = label.split('|')[-1].strip()
                    else:
                        item_name = label
                    
                    match = re.search(r'__(\d+)', fvar)
                    if match:
                        item_num = int(match.group(1))
                        filter_items[item_num] = item_name
            
            section.append(f"\n* {code} - {q_info['text'][:60]}... (filtrováno podle {filter_q}).")
            
            # Seřadit proměnné numericky podle čísla za __
            sorted_vars = sorted(variables, key=lambda x: int(re.search(r'_(\d+)$', x).group(1)) if re.search(r'_(\d+)$', x) else 0)
            
            for var in sorted_vars:
                # Extrahovat číslo itemu
                match = re.search(r'_(\d+)$', var)
                if match:
                    item_num = int(match.group(1))
                    filter_item_name = filter_items.get(item_num, f"Item {item_num}")
                    # Label: POUZE název společnosti/položky
                    section.append(f'VAR LAB {var} "{filter_item_name}".')
            
            section.append("EXECUTE.")
            
            # Pokud je to FILTRACE ODPOVĚDÍ (dichotomická MR), vytvořit MDGROUP
            if q_info.get('type') and 'FILTRACE ODPOVĚDÍ' in q_info['type']:
                # Kontrola, že jsou to dichotomické hodnoty (0,1,2)
                if variables:
                    first_var = variables[0]
                    unique_vals = set(self.df[first_var].dropna().unique())
                    if unique_vals.issubset({0, 1, 2, 0.0, 1.0, 2.0}):
                        # Najít i vlastní options z dotazníku (např. QA3__1 = "Žádné z uvedených")
                        # Pattern: Q{code}__{number} (jednoduchá baterie, ne filtrovaná)
                        own_options = []
                        for col in self.df.columns:
                            # Hledat Q{code}__{num} kde není další podtržítko (není to filtrovaná)
                            pattern = f'^Q{code}__\\d+$'
                            if re.match(pattern, col):
                                # Zkontrolovat že má dichotomické hodnoty
                                col_vals = set(self.df[col].dropna().unique())
                                if col_vals.issubset({0, 1, 2, 0.0, 1.0, 2.0}):
                                    own_options.append(col)
                        
                        # Seřadit vlastní options
                        own_options = sorted(own_options, key=lambda x: int(re.search(r'__(\d+)', x).group(1)) if re.search(r'__(\d+)', x) else 0)
                        
                        # Přidat labely pro vlastní options
                        if own_options:
                            section.append(f"* Vlastní options pro {code}:")
                            for i, var in enumerate(own_options):
                                if i < len(q_info.get('options', [])):
                                    option_text = q_info['options'][i]
                                    section.append(f'VAR LAB {var} "{option_text}".')
                            section.append("EXECUTE.")
                        
                        # Je to dichotomická MR, vytvořit MDGROUP
                        # Kombinovat filtrované + vlastní options
                        all_vars = sorted_vars + own_options
                        var_list = ' '.join(all_vars)
                        mrset_name = f"${code.lower()}"
                        mrsets_cmd = f"""
* Vytvoření MR setu pro {code}.
MRSETS
  /MDGROUP NAME={mrset_name} CATEGORYLABELS=VARLABELS 
  VARIABLES={var_list} VALUE=2
  /DISPLAY NAME=[{mrset_name}]."""
                        mrsets_commands.append(mrsets_cmd)
        
        if len(section) > 1:
            self.syntax_parts.append('\n'.join(section))
            if mrsets_commands:
                self.syntax_parts.append('\n'.join(mrsets_commands))
    
    def _generate_filtered_mr_batteries(self, filtered_mr_batteries: Dict[str, Dict]):
        """Generuje VAR LAB a MCGROUP pro filtrované MR baterie (např. B2__A2_1column1)"""
        if not filtered_mr_batteries:
            return
            
        section = ["* VARIABLE LABELS PRO FILTROVANÉ MR BATERIE."]
        mrsets_commands = []
        
        for code, info in sorted(filtered_mr_batteries.items()):
            filter_q = info['filter']
            variables = info['vars']
            
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
            
            # Pro FILTRACE ODPOVĚDÍ použít options ze zdrojové otázky pro společnosti
            filter_q_info = self.questionnaire.get(filter_q)
            use_filter_options = False
            
            if q_info.get('type') and 'FILTRACE ODPOVĚDÍ' in q_info['type']:
                if filter_q_info and filter_q_info.get('options'):
                    use_filter_options = True
            
            # Získat názvy položek z filtrační otázky (např. A2 = společnosti)
            filter_items = {}
            
            if use_filter_options:
                # Použít options z dotazníku filtrační otázky
                for i, option in enumerate(filter_q_info['options'], 1):
                    filter_items[i] = option
            else:
                # Jinak extrahovat z labelů proměnných
                filter_vars = [col for col in self.df.columns if col.startswith(f'Q{filter_q}__')]
                for fvar in filter_vars:
                    label = self.meta.column_names_to_labels.get(fvar, '')
                    if '\n' in label:
                        item_name = label.split('\n')[-1].strip()
                    elif '|' in label:
                        item_name = label.split('|')[-1].strip()
                    else:
                        item_name = label
                    
                    match = re.search(r'__(\d+)', fvar)
                    if match:
                        item_num = int(match.group(1))
                        filter_items[item_num] = item_name
            
            # Získat názvy sloupců (atributů) z otázky code
            column_items = {}
            if q_info.get('options'):
                for i, opt in enumerate(q_info['options'], 1):
                    column_items[i] = opt
            
            section.append(f"\n* {code} - {q_info['text'][:60]}... (filtrováno podle {filter_q}).")
            
            # Seřadit proměnné podle company a column
            def sort_key(var):
                match = re.match(r'Q[A-Z]\d+[a-z]?__[A-Z]\d+[a-z]?_(\d+)column(\d+)', var)
                if match:
                    return (int(match.group(1)), int(match.group(2)))
                return (0, 0)
            
            sorted_vars = sorted(variables, key=sort_key)
            
            for var in sorted_vars:
                match = re.match(r'Q[A-Z]\d+[a-z]?__[A-Z]\d+[a-z]?_(\d+)column(\d+)', var)
                if match:
                    company_num = int(match.group(1))
                    column_num = int(match.group(2))
                    
                    filter_item_name = filter_items.get(company_num, f"Item {company_num}")
                    column_name = column_items.get(column_num, f"Column {column_num}")
                    
                    # Label: POUZE atribut (společnost bude v názvu MR setu)
                    section.append(f'VAR LAB {var} "{column_name}".')
            
            section.append("EXECUTE.")
            
            # Vytvořit MCGROUP pro každou společnost (všechny columny pro jednu společnost)
            # Seskupit proměnné podle company_num
            companies_vars = {}
            for var in sorted_vars:
                match = re.match(r'Q[A-Z]\d+[a-z]?__[A-Z]\d+[a-z]?_(\d+)column(\d+)', var)
                if match:
                    company_num = int(match.group(1))
                    if company_num not in companies_vars:
                        companies_vars[company_num] = []
                    companies_vars[company_num].append(var)
            
            # Vytvořit MDGROUP pro každou společnost (dichotomická MR - hodnoty 0/1)
            for company_num in sorted(companies_vars.keys()):
                company_vars = companies_vars[company_num]
                filter_item_name = filter_items.get(company_num, f"Item {company_num}")
                
                # Seřadit podle column čísla
                company_vars_sorted = sorted(company_vars, key=lambda x: int(re.search(r'column(\d+)', x).group(1)) if re.search(r'column(\d+)', x) else 0)
                
                var_list = ' '.join(company_vars_sorted)
                # Název setu: ${code}_${company_num} např. $b2_1
                mrset_name = f"${code.lower()}_{company_num}"
                mrsets_cmd = f"""
* Vytvoření MR setu pro {code} - {filter_item_name}.
MRSETS
  /MDGROUP NAME={mrset_name} CATEGORYLABELS=VARLABELS 
  VARIABLES={var_list} VALUE=1
  /DISPLAY NAME=[{mrset_name}]."""
                mrsets_commands.append(mrsets_cmd)
        
        if len(section) > 1:
            self.syntax_parts.append('\n'.join(section))
            if mrsets_commands:
                self.syntax_parts.append('\n'.join(mrsets_commands))
    
    def _generate_single_open(self, single_open: List[str]):
        """Generuje VAR LAB pro jednopólové otevřené otázky (QK1, QB1) a MCGROUP pro nakódované verze"""
        if not single_open:
            return
            
        section = ["* VARIABLE LABELS PRO JEDNOPÓLOVÉ OTEVŘENÉ OTÁZKY."]
        mrsets_commands = []
        
        for var_name in sorted(single_open):
            # Extrahovat kód otázky
            match = re.match(r'^Q([A-Z]\d+[a-z]?)$', var_name)
            if not match:
                continue
                
            code = match.group(1)
            q_info = self.questionnaire.get(code)
            if not q_info:
                continue
            
            section.append(f"\n* {code} - {q_info['text'][:60]}...")
            
            # Variable label pro stringovou verzi
            full_text = q_info['text']
            section.append(f'VAR LAB {var_name} "{full_text}".')
            section.append("EXECUTE.")
            
            # Zkontrolovat nakódované verze
            coded_vars = []
            for col in self.df.columns:
                if col.startswith(f'Q{code}_') and '__' not in col and '_jina' not in col:
                    suffix = col[len(f'Q{code}_'):]
                    if suffix.isdigit():
                        if self.df[col].dtype in ['int64', 'float64']:
                            coded_vars.append(col)
            
            if coded_vars:
                coded_vars = sorted(coded_vars, key=lambda x: int(x.split('_')[-1]))
                
                section.append(f"* Nakódované odpovědi pro {code}:")
                for coded_var in coded_vars:
                    section.append(f'VAR LAB {coded_var} "{full_text}".')
                section.append("EXECUTE.")
                
                # MRSETS command
                var_list = ' '.join(coded_vars)
                mrset_name = f"${code.lower()}"
                mrsets_cmd = f"""
* Vytvoření MR setu pro nakódované odpovědi {code}.
MRSETS
  /MCGROUP NAME={mrset_name} VARIABLES={var_list}
  /DISPLAY NAME=[{mrset_name}]."""
                mrsets_commands.append(mrsets_cmd)
        
        if len(section) > 1:
            self.syntax_parts.append('\n'.join(section))
            if mrsets_commands:
                self.syntax_parts.append('\n'.join(mrsets_commands))
    
    def save_syntax(self, output_path: str):
        """Uloží vygenerovanou syntax do souboru s správným kódováním pro SPSS"""
        syntax = self.generate_syntax()
        
        # SPSS v češtině používá Windows-1250 (CP1250) kódování
        # A Windows-style line endings (CRLF)
        with open(output_path, 'w', encoding='cp1250', newline='\r\n') as f:
            f.write(syntax)
        print(f"\n💾 Syntax uložena do: {output_path}")
        print(f"   Kódování: Windows-1250 (CP1250)")
        print(f"   Konce řádků: CRLF (Windows)")
        
    def run(self, output_path: str):
        """Spustí celý proces"""
        print("="*80)
        print("SPSS SYNTAX GENERATOR")
        print("="*80)
        
        self.load_data()
        self.load_questionnaire()
        self.save_syntax(output_path)
        
        print("\n✅ HOTOVO!")
        return output_path


def main():
    """Hlavní funkce pro testování"""
    generator = SPSSSyntaxGenerator(
        data_path='/mnt/user-data/uploads/Data_puvodni.sav',
        questionnaire_path='/mnt/user-data/uploads/Herbadent_tracking_značky_25_-_2026-01-13.docx'
    )
    
    output_path = '/home/claude/generated_syntax.sps'
    generator.run(output_path)
    
    return output_path


if __name__ == '__main__':
    main()

# Flask API
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile

app = Flask(__name__)
CORS(app)

@app.route('/api/generate', methods=['POST'])
def generate_syntax():
    """API endpoint pro generování syntax"""
    try:
        if 'sav_file' not in request.files or 'docx_file' not in request.files:
            return jsonify({'error': 'Chybí soubory'}), 400
        
        sav_file = request.files['sav_file']
        docx_file = request.files['docx_file']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            sav_path = os.path.join(tmpdir, 'data.sav')
            docx_path = os.path.join(tmpdir, 'questionnaire.docx')
            output_path = os.path.join(tmpdir, 'syntax.sps')
            
            sav_file.save(sav_path)
            docx_file.save(docx_path)
            
            generator = SPSSSyntaxGenerator(sav_path, docx_path)
            generator.run(output_path)
            
            return send_file(
                output_path,
                mimetype='text/plain',
                as_attachment=True,
                download_name='generated_syntax.sps'
            )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
