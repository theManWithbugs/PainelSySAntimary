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
`imagens[].url`.

Os registros individuais contêm informações pessoais. A página inicial e a API
de moradores ficam restritas a usuários internos com acesso de staff no Django.
Crie um usuário administrador com:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
```

Entre pela tela do Django Admin antes de abrir o mapa. Em produção, configure
`DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` para o domínio
interno antes de iniciar o serviço.

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

O mapa e os dados de moradores continuam protegidos por login de staff. O
`health/` é público para a verificação de disponibilidade do Render.
