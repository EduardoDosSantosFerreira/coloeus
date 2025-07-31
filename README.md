# Coloeus

**Coloeus** é uma poderosa ferramenta para Windows que oferece uma interface programática para **gerenciamento de programas instalados**, **análise de arquivos**, **uso de disco** e **controle de permissões administrativas**. Ideal para administradores de sistema, técnicos e usuários avançados que desejam controlar e otimizar seus sistemas Windows com segurança e eficiência.

---

## 🔧 Funcionalidades

### 👮‍♂️ Execução com privilégios administrativos

* Verifica se o script está sendo executado como administrador.
* Relança automaticamente o script com privilégios de administrador, caso necessário.

### 📦 Gerenciador de Programas Instalados

* Lista todos os programas instalados no sistema (com opção de incluir atualizações do Windows).
* Coleta informações como:

  * Nome
  * Versão
  * Tamanho estimado
  * Caminho de desinstalação
  * Local de instalação
  * Editora/publisher
  * Ícone do programa
* Ordena os programas por tamanho e nome.
* Permite **desinstalar** qualquer programa detectado, com suporte a comandos MSI e executáveis padrão.

### 🗂️ Scanner de Arquivos

* Escaneia diretórios e retorna arquivos com base em filtros:

  * Tamanho mínimo e máximo (em bytes)
  * Extensões específicas (`.exe`, `.txt`, etc.)
  * Inclusão de subdiretórios ou não
* Detecta e lista arquivos e pastas com detalhes como:

  * Caminho
  * Tamanho
  * Último acesso
  * Última modificação
  * Extensão
* Ideal para localizar arquivos grandes ou indesejados no sistema.

### 🧹 Gerenciamento de Arquivos

* Deleta arquivos e diretórios, com tratamento de erros e reelevação automática de privilégios caso necessário.
* Abre o **Explorer** diretamente na pasta de um arquivo específico.
* Consulta propriedades detalhadas de qualquer arquivo ou pasta.

### 💽 Monitoramento de Disco

* Coleta estatísticas de uso de disco:

  * Espaço total, utilizado e livre
  * Percentual de uso
* Usa **cache de 5 segundos** para evitar chamadas redundantes.

---

## 🛠️ Requisitos

* **Sistema Operacional**: Windows 10 ou superior
* **Python**: 3.8 ou superior
* Execução como **Administrador** (requisito automático no script)

---

## 🚀 Como Usar

1. Execute o script `Coloeus.py`.
2. O script verificará e solicitará permissões administrativas.
3. Utilize os métodos da classe `SystemScanner` para interagir com o sistema:

```python
from Coloeus import SystemScanner

# Listar programas instalados
programas = SystemScanner.get_installed_programs()

# Escanear arquivos acima de 100 MB no diretório C:\
arquivos = SystemScanner.scan_files(["C:\\"], min_size=100 * 1024 * 1024)

# Ver estatísticas de disco
uso_disco = SystemScanner.get_disk_usage("C:\\")

# Deletar um arquivo
SystemScanner.delete_file("C:\\Users\\Example\\Downloads\\arquivo_grande.txt")
```

---

## 📁 Estrutura Interna

* `ProgramInfo`: Estrutura de dados para representar programas instalados.
* `FileInfo`: Estrutura de dados para representar arquivos encontrados.
* `SystemScanner`: Classe principal com todos os métodos utilitários.

---

## 🔐 Segurança

* Todas as operações sensíveis (desinstalação, deleção, execução de comandos) são executadas com checagem e/ou elevação de privilégios administrativos.
* Uso de `ShellExecuteW` para operações seguras em ambiente Windows.

---

## ⚠️ Avisos

> ⚠ **Atenção:** A manipulação de arquivos e programas pode causar perda de dados ou mau funcionamento do sistema se usada incorretamente. Utilize este software com responsabilidade.

---

## 📄 Licença

Este projeto está sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

---
