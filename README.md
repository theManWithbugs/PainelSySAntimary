# Painel territorial do Antimary

## Configuração local

Instale as dependências:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

O mapa procura a credencial local em
`%LOCALAPPDATA%\Antimary\firebase-service-account.json`. Você também pode
configurar `FIREBASE_SERVICE_ACCOUNT_PATH` para outro caminho. Mantenha o
arquivo fora do repositório e não o envie ao controle de versão. No PowerShell:

```powershell
$env:FIREBASE_SERVICE_ACCOUNT_PATH = "$env:LOCALAPPDATA\Antimary\firebase-service-account.json"
```

O mapa lê a coleção `moradores` do Cloud Firestore e usa `localizacao` no formato
`latitude, longitude`. Fotos são carregadas das URLs HTTPS do Cloudinary em
`imagens[].url`. Ao selecionar um registro no mapa, também são exibidos os
moradores vinculados em `moradores[]`; CPF e telefone desses moradores não são
retornados pela API.

O mapa e a API de moradores exigem o PIN `1242`; após informá-lo, o acesso fica
liberado na sessão do navegador. Esse PIN fixo é uma barreira simples e não
substitui autenticação adequada para proteger informações confidenciais.
Após o acesso, a página `/indicadores/` apresenta um resumo dos cadastros por
colônia e gênero informado dos moradores vinculados, além da lista de registros.
Selecione o nome de um cadastro para abrir sua ficha detalhada, com os campos
disponíveis, moradores vinculados e imagens autorizadas.
Use **Gerar relatório PDF** para abrir a impressão do navegador e salvar os
indicadores e a lista completa de cadastros como PDF.
Publique somente registros e fotos autorizados para divulgação. O Django Admin
continua protegido por autenticação. Se precisar administrar o site, crie um
usuário administrador com:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
```

Entre pela tela do Django Admin para administração. Em produção, configure
`DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` para o domínio
antes de iniciar o serviço.

## Publicar no Render

1. Envie o projeto para um repositório Git privado e crie um PostgreSQL
   persistente no Render (a instância do PostgreSQL pode ter custo próprio;
   confira o plano antes de criá-la). Não envie `db.sqlite3`, a pasta `venv`
   nem a chave do Firebase.
2. No Render, crie um **Blueprint** a partir do repositório e selecione
   `render.yaml`. Informe a URL interna do PostgreSQL para `DATABASE_URL`.
3. Configure `FIREBASE_SERVICE_ACCOUNT_JSON` como variável secreta, usando o
   conteúdo do JSON da service account. Nunca adicione esse conteúdo ao
   repositório ou ao `render.yaml`.
4. O Blueprint gera `DJANGO_SECRET_KEY`, coleta os arquivos estáticos e aplica
   as migrações na inicialização. O Render informa `RENDER_EXTERNAL_HOSTNAME`,
   usado automaticamente para os hosts e CSRF.
5. Selecione **Environment** no serviço e adicione temporariamente as variáveis
   secretas `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e
   `DJANGO_SUPERUSER_PASSWORD`, com uma senha forte. O comando de inicialização
   cria o primeiro usuário interno; depois da publicação, remova essas três
   variáveis e entre em `/admin/` com a conta criada.

O mapa, a API de moradores e `health/` são públicos. O Django Admin continua
protegido por login.
