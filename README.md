# Filmow Media Collection Exporter

Um script Python para extrair, organizar e exportar suas coleções de filmes e séries do Filmow.com em diversos formatos.

## Descrição

O Filmow Media Collection Exporter permite que você extraia facilmente todos os filmes e séries da sua conta no Filmow.com e os exporte para múltiplos formatos úteis, como JSON, Excel e CSV. O script organiza automaticamente seus conteúdos em categorias (Já vi, Favoritos, Quero ver) e oferece várias opções de ordenação.

## Funcionalidades

- Extração completa de filmes e séries dos perfis do Filmow
- Categorização automática em "Já vi", "Favoritos" e "Quero ver"
- Múltiplas opções de ordenação (título, avaliação, favoritos)
- Exportação para vários formatos (JSON, Excel, CSV)
- Suporte para português e inglês
- Multithreading para aceleração da extração
- Log detalhado de operações

## Requisitos

O script instalará automaticamente as dependências necessárias, mas você também pode instalá-las manualmente:

```bash
pip install requests pandas beautifulsoup4 tqdm openpyxl colorama argparse
```

Além disso, o script depende dos módulos `filmow_scraper.py` e `media_sorter.py` que devem estar no mesmo diretório.

## Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/filmow-exporter.git
   cd filmow-exporter
   ```

2. Certifique-se de que você tem o Python 3.6+ instalado.

3. Execute o script conforme instruído na seção "Uso".

## Guia para Iniciantes

Se você tem pouca experiência com programação ou linha de comando, siga este guia passo a passo para executar o script:

### 1. Instalar o Python

1. Acesse [python.org](https://www.python.org/downloads/) e baixe a versão mais recente do Python (3.6 ou superior)
2. Execute o instalador baixado
3. **IMPORTANTE**: Marque a opção "Add Python to PATH" durante a instalação
4. Clique em "Install Now"

### 2. Baixar os arquivos do projeto

1. Clique no botão verde "Code" na página principal deste repositório
2. Selecione "Download ZIP"
3. Descompacte o arquivo ZIP em uma pasta de sua preferência, como "Meus Documentos"

### 3. Baixar os arquivos necessários

Certifique-se de que você tem os seguintes arquivos na mesma pasta:
- `main.py` (o script principal)
- `filmow_scraper.py`
- `media_sorter.py`

### 4. Executar o script

#### No Windows:
1. Abra a pasta onde você salvou os arquivos
2. Segure a tecla Shift e clique com o botão direito em um espaço vazio da pasta
3. Selecione "Abrir janela do PowerShell aqui" ou "Abrir janela de comando aqui"
4. Na janela que abrir, digite:
   ```
   python main.py
   ```
5. Pressione Enter
6. Quando solicitado, digite seu nome de usuário do Filmow

#### No macOS:
1. Abra o aplicativo Terminal (você pode encontrá-lo pesquisando "Terminal" no Spotlight)
2. Digite `cd ` (com um espaço após "cd")
3. Arraste a pasta onde você salvou os arquivos para a janela do Terminal e solte
4. Pressione Enter
5. Digite:
   ```
   python3 main.py
   ```
6. Pressione Enter
7. Quando solicitado, digite seu nome de usuário do Filmow

#### No Linux:
1. Abra o Terminal
2. Navegue até a pasta onde você salvou os arquivos usando o comando `cd`
3. Digite:
   ```
   python3 main.py
   ```
4. Pressione Enter
5. Quando solicitado, digite seu nome de usuário do Filmow

### 5. Encontrar os arquivos exportados

1. O script criará uma pasta chamada "output" no mesmo local onde você executou o script
2. Dentro desta pasta, você encontrará seus arquivos exportados com o formato:
   - `filmow_[seu_usuario]_[data_hora].json`
   - `filmow_[seu_usuario]_[data_hora].xlsx`
   - Uma pasta `filmow_[seu_usuario]_[data_hora]_csv` contendo vários arquivos CSV

### Solução de problemas comuns

- **"Python não é reconhecido como um comando interno"**: Você precisa reinstalar o Python marcando a opção "Add Python to PATH"
- **"Módulo não encontrado"**: O script tentará instalar os módulos necessários automaticamente. Se isso falhar, você pode instalá-los manualmente executando:
  ```
  pip install requests pandas beautifulsoup4 tqdm openpyxl colorama argparse
  ```
- **"Arquivos não encontrados"**: Certifique-se de que `main.py`, `filmow_scraper.py` e `media_sorter.py` estão na mesma pasta
- **Processo muito lento**: Você pode ajustar o número de workers com a opção `--workers 3` para reduzir a carga

## Uso

Você pode executar o script com uma variedade de opções:

```bash
python main.py --username seu_usuario_filmow --output-dir output --formats all --sort rating
```

### Opções disponíveis

| Opção | Descrição |
|-------|-----------|
| `--username`, `-u` | Nome de usuário do Filmow (se não fornecido, irá solicitar) |
| `--output-dir`, `-o` | Diretório para arquivos de saída (padrão: 'output') |
| `--formats`, `-f` | Formatos de saída: json, xlsx, csv, all (padrão: 'all') |
| `--sort`, `-s` | Critério principal de ordenação: title, rating, favorite, none (padrão: 'title') |
| `--movies-only` | Extrair apenas filmes, ignorar séries |
| `--tv-only` | Extrair apenas séries, ignorar filmes |
| `--log-level` | Nível de logging: DEBUG, INFO, WARNING, ERROR (padrão: 'INFO') |
| `--workers` | Número de threads concorrentes (padrão: 5) |
| `--timeout` | Tempo limite de requisição em segundos (padrão: 10) |
| `--language`, `-l` | Idioma da interface: pt, en (padrão: 'pt') |

### Exemplos

1. Extração básica solicitando o nome de usuário:
   ```bash
   python main.py
   ```

2. Exportar apenas para JSON e ordenar por avaliação:
   ```bash
   python main.py -u seu_usuario -f json -s rating
   ```

3. Extrair apenas séries e exportar para Excel:
   ```bash
   python main.py -u seu_usuario --tv-only -f xlsx
   ```

4. Extrair dados em inglês com alto nível de detalhamento nos logs:
   ```bash
   python main.py -u seu_usuario -l en --log-level DEBUG
   ```

## Estrutura dos dados

Os dados são organizados nas seguintes categorias:

- **Filmes - Já vi**: Filmes marcados como assistidos
- **Filmes - Favoritos**: Filmes marcados como favoritos
- **Filmes - Quero ver**: Filmes na lista de interesse
- **Séries - Já vi**: Séries marcadas como assistidas
- **Séries - Favoritos**: Séries marcadas como favoritas
- **Séries - Quero ver**: Séries na lista de interesse

## Solução de problemas

Se você encontrar problemas:

1. Verifique se `filmow_scraper.py` e `media_sorter.py` estão no mesmo diretório que `main.py`
2. Tente aumentar o tempo limite com `--timeout 20`
3. Se houver problemas de conexão, reduza o número de workers com `--workers 3`
4. Verifique o arquivo de log `filmow_export.log` para mais detalhes

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Nota

Este projeto não é afiliado oficialmente ao Filmow.com. É uma ferramenta de comunidade para uso pessoal.
