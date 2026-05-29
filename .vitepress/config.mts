import { defineConfig } from 'vitepress'

function navFr() {
  return [
    { text: 'Tutoriel',        link: '/fr/tutorials/getting-started', activeMatch: '/fr/tutorials/' },
    { text: 'Guides pratiques',link: '/fr/how-to/add-new-domain',     activeMatch: '/fr/how-to/' },
    { text: 'Explications',    link: '/fr/explanation/architecture',  activeMatch: '/fr/explanation/' },
    { text: 'Référence',       link: '/fr/reference/configuration',   activeMatch: '/fr/reference/' },
    { text: 'v1.0.0', items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
  ]
}

function navZh() {
  return [
    { text: '教程',     link: '/zh/tutorials/getting-started', activeMatch: '/zh/tutorials/' },
    { text: '操作指南', link: '/zh/how-to/add-new-domain',     activeMatch: '/zh/how-to/' },
    { text: '概念解析', link: '/zh/explanation/architecture',  activeMatch: '/zh/explanation/' },
    { text: '参考文档', link: '/zh/reference/configuration',   activeMatch: '/zh/reference/' },
    { text: 'v1.0.0', items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
  ]
}

function navDe() {
  return [
    { text: 'Tutorial',     link: '/de/tutorials/getting-started', activeMatch: '/de/tutorials/' },
    { text: 'Anleitungen',  link: '/de/how-to/add-new-domain',     activeMatch: '/de/how-to/' },
    { text: 'Erklärungen',  link: '/de/explanation/architecture',  activeMatch: '/de/explanation/' },
    { text: 'Referenz',     link: '/de/reference/configuration',   activeMatch: '/de/reference/' },
    { text: 'v1.0.0', items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
  ]
}

function navPtBr() {
  return [
    { text: 'Tutorial',   link: '/pt-br/tutorials/getting-started', activeMatch: '/pt-br/tutorials/' },
    { text: 'Guias',      link: '/pt-br/how-to/add-new-domain',     activeMatch: '/pt-br/how-to/' },
    { text: 'Explicações',link: '/pt-br/explanation/architecture',  activeMatch: '/pt-br/explanation/' },
    { text: 'Referência', link: '/pt-br/reference/configuration',   activeMatch: '/pt-br/reference/' },
    { text: 'v1.0.0', items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
  ]
}

function sidebarFr() {
  return {
    '/fr/tutorials/': [{ text: 'Tutoriels', items: [
      { text: 'Premiers pas',          link: '/fr/tutorials/getting-started' },
      { text: 'Implémenter un domaine',link: '/fr/tutorials/first-domain' },
    ]}],
    '/fr/how-to/': [
      { text: 'Mise en place', items: [
        { text: 'Nouveau projet',                         link: '/fr/how-to/new-project' },
        { text: 'Ajouter un domaine',                    link: '/fr/how-to/add-new-domain' },
        { text: 'Implémenter un dépôt SQLAlchemy',       link: '/fr/how-to/sqlalchemy-repository' },
        { text: 'Configurer l\'authentification',        link: '/fr/how-to/configure-auth' },
        { text: 'Middleware d\'auth personnalisé',        link: '/fr/how-to/custom-auth-middleware' },
        { text: 'Configurer MCP',                        link: '/fr/howto/mcp-setup' },
      ]},
      { text: 'Patrons', items: [
        { text: 'Patrons de réponse',         link: '/fr/how-to/response-patterns' },
        { text: 'Gérer les erreurs de validation', link: '/fr/how-to/validation' },
        { text: 'RFC 9457 Problem Details',   link: '/fr/how-to/problem-details' },
        { text: 'Injection de dépendances',   link: '/fr/how-to/dependency-injection' },
        { text: 'Ordre du middleware',         link: '/fr/how-to/middleware-stack' },
        { text: 'Lifespan & app.state',        link: '/fr/how-to/lifespan-and-app-state' },
        { text: 'UseCase asynchrone',          link: '/fr/how-to/async-use-case' },
        { text: 'Patrons de concurrence',      link: '/fr/how-to/concurrency-patterns' },
        { text: 'Tâches en arrière-plan',      link: '/fr/how-to/background-tasks' },
        { text: 'Événements de domaine',       link: '/fr/how-to/domain-events' },
        { text: 'Suppression logique',         link: '/fr/how-to/soft-delete' },
        { text: 'Versionnage d\'API',          link: '/fr/how-to/api-versioning' },
        { text: 'CORS',                        link: '/fr/how-to/cors' },
      ]},
      { text: 'E/S, données & saisie', items: [
        { text: 'Téléversement de fichiers',   link: '/fr/how-to/file-upload' },
        { text: 'Réponses en streaming',       link: '/fr/how-to/streaming' },
        { text: 'Journalisation structurée',   link: '/fr/how-to/structured-logging' },
        { text: 'Webhook & HMAC',              link: '/fr/how-to/webhook' },
        { text: 'Decimal & saisie Unicode',    link: '/fr/how-to/decimal-unicode-input' },
        { text: 'Analyse d\'e-mail',           link: '/fr/how-to/email-address-parsing' },
      ]},
      { text: 'Tests & déploiement', items: [
        { text: 'Exécuter les tests',          link: '/fr/how-to/run-tests' },
        { text: 'Tests DB réels',              link: '/fr/how-to/run-integration-tests' },
        { text: 'Publier sur PyPI',            link: '/fr/how-to/release-and-publish' },
      ]},
    ],
    '/fr/explanation/': [{ text: 'Explications', items: [
      { text: 'Architecture',                        link: '/fr/explanation/architecture' },
      { text: 'Philosophie de conception',           link: '/fr/explanation/design-philosophy' },
      { text: 'Un UseCase, deux surfaces',           link: '/fr/explanation/one-usecase-two-surfaces' },
      { text: 'Méthodologie des essais terrain',     link: '/fr/explanation/field-trial-methodology' },
    ]}],
    '/fr/reference/': [{ text: 'Référence', items: [
      { text: 'Configuration',         link: '/fr/reference/configuration' },
      { text: 'Modules du framework',  link: '/fr/reference/framework-modules' },
      { text: 'REST API',              link: '/fr/reference/api' },
    ]}],
  }
}

function sidebarZh() {
  return {
    '/zh/tutorials/': [{ text: '教程', items: [
      { text: '快速上手',        link: '/zh/tutorials/getting-started' },
      { text: '实现第一个领域',  link: '/zh/tutorials/first-domain' },
    ]}],
    '/zh/how-to/': [
      { text: '基础操作', items: [
        { text: '新建项目',                link: '/zh/how-to/new-project' },
        { text: '添加新领域',              link: '/zh/how-to/add-new-domain' },
        { text: '实现 SQLAlchemy 存储库',  link: '/zh/how-to/sqlalchemy-repository' },
        { text: '配置身份认证',            link: '/zh/how-to/configure-auth' },
        { text: '自定义认证中间件',        link: '/zh/how-to/custom-auth-middleware' },
        { text: '配置 MCP',               link: '/zh/howto/mcp-setup' },
      ]},
      { text: '开发模式', items: [
        { text: '响应模式',        link: '/zh/how-to/response-patterns' },
        { text: '处理验证错误',    link: '/zh/how-to/validation' },
        { text: 'RFC 9457 问题详情',link: '/zh/how-to/problem-details' },
        { text: '依赖注入',        link: '/zh/how-to/dependency-injection' },
        { text: '中间件栈配置',    link: '/zh/how-to/middleware-stack' },
        { text: 'Lifespan 与 app.state', link: '/zh/how-to/lifespan-and-app-state' },
        { text: '异步 UseCase',    link: '/zh/how-to/async-use-case' },
        { text: '并发模式选择',    link: '/zh/how-to/concurrency-patterns' },
        { text: '后台任务',        link: '/zh/how-to/background-tasks' },
        { text: '领域事件模式',    link: '/zh/how-to/domain-events' },
        { text: '软删除（逻辑删除）',link: '/zh/how-to/soft-delete' },
        { text: 'API 版本控制',    link: '/zh/how-to/api-versioning' },
        { text: 'CORS 配置',       link: '/zh/how-to/cors' },
      ]},
      { text: 'I/O、数据与输入', items: [
        { text: '文件上传',        link: '/zh/how-to/file-upload' },
        { text: '流式响应',        link: '/zh/how-to/streaming' },
        { text: '结构化日志',      link: '/zh/how-to/structured-logging' },
        { text: 'Webhook 与 HMAC', link: '/zh/how-to/webhook' },
        { text: 'Decimal 与 Unicode 输入', link: '/zh/how-to/decimal-unicode-input' },
        { text: '电子邮件地址解析',link: '/zh/how-to/email-address-parsing' },
      ]},
      { text: '测试与发布', items: [
        { text: '运行测试',        link: '/zh/how-to/run-tests' },
        { text: '真实数据库集成测试',link: '/zh/how-to/run-integration-tests' },
        { text: '发布到 PyPI',     link: '/zh/how-to/release-and-publish' },
      ]},
    ],
    '/zh/explanation/': [{ text: '概念解析', items: [
      { text: '架构概述',              link: '/zh/explanation/architecture' },
      { text: '设计理念',              link: '/zh/explanation/design-philosophy' },
      { text: '一个 UseCase，两个接口',link: '/zh/explanation/one-usecase-two-surfaces' },
      { text: '现场试验方法论',        link: '/zh/explanation/field-trial-methodology' },
    ]}],
    '/zh/reference/': [{ text: '参考文档', items: [
      { text: '配置参考',      link: '/zh/reference/configuration' },
      { text: '框架模块',      link: '/zh/reference/framework-modules' },
      { text: 'REST API',      link: '/zh/reference/api' },
    ]}],
  }
}

function sidebarDe() {
  return {
    '/de/tutorials/': [{ text: 'Tutorials', items: [
      { text: 'Erste Schritte',          link: '/de/tutorials/getting-started' },
      { text: 'Erste Domain implementieren', link: '/de/tutorials/first-domain' },
    ]}],
    '/de/how-to/': [
      { text: 'Einstieg', items: [
        { text: 'Neues Projekt',                       link: '/de/how-to/new-project' },
        { text: 'Neue Domain hinzufügen',              link: '/de/how-to/add-new-domain' },
        { text: 'SQLAlchemy-Repository implementieren',link: '/de/how-to/sqlalchemy-repository' },
        { text: 'Authentifizierung konfigurieren',     link: '/de/how-to/configure-auth' },
        { text: 'Eigene Auth-Middleware',              link: '/de/how-to/custom-auth-middleware' },
        { text: 'MCP einrichten',                      link: '/de/howto/mcp-setup' },
      ]},
      { text: 'Muster', items: [
        { text: 'Antwortmuster',           link: '/de/how-to/response-patterns' },
        { text: 'Validierungsfehler',      link: '/de/how-to/validation' },
        { text: 'RFC 9457 Problem Details',link: '/de/how-to/problem-details' },
        { text: 'Abhängigkeitsinjektion',  link: '/de/how-to/dependency-injection' },
        { text: 'Middleware-Stack',        link: '/de/how-to/middleware-stack' },
        { text: 'Lifespan & app.state',    link: '/de/how-to/lifespan-and-app-state' },
        { text: 'Asynchrone UseCases',     link: '/de/how-to/async-use-case' },
        { text: 'Parallelitätsmuster',     link: '/de/how-to/concurrency-patterns' },
        { text: 'Hintergrundaufgaben',     link: '/de/how-to/background-tasks' },
        { text: 'Domänenereignisse',       link: '/de/how-to/domain-events' },
        { text: 'Soft Delete',             link: '/de/how-to/soft-delete' },
        { text: 'API-Versionierung',       link: '/de/how-to/api-versioning' },
        { text: 'CORS',                    link: '/de/how-to/cors' },
      ]},
      { text: 'E/A, Daten & Eingabe', items: [
        { text: 'Datei-Upload',            link: '/de/how-to/file-upload' },
        { text: 'Streaming-Antworten',     link: '/de/how-to/streaming' },
        { text: 'Strukturiertes Logging',  link: '/de/how-to/structured-logging' },
        { text: 'Webhook & HMAC',          link: '/de/how-to/webhook' },
        { text: 'Decimal & Unicode-Eingabe',link: '/de/how-to/decimal-unicode-input' },
        { text: 'E-Mail-Adressen parsen',  link: '/de/how-to/email-address-parsing' },
      ]},
      { text: 'Tests & Veröffentlichung', items: [
        { text: 'Tests ausführen',         link: '/de/how-to/run-tests' },
        { text: 'Echtdatenbank-Tests',     link: '/de/how-to/run-integration-tests' },
        { text: 'Auf PyPI veröffentlichen',link: '/de/how-to/release-and-publish' },
      ]},
    ],
    '/de/explanation/': [{ text: 'Erklärungen', items: [
      { text: 'Architekturübersicht',          link: '/de/explanation/architecture' },
      { text: 'Designphilosophie',             link: '/de/explanation/design-philosophy' },
      { text: 'Ein UseCase, zwei Oberflächen', link: '/de/explanation/one-usecase-two-surfaces' },
      { text: 'Feldversuchs-Methodik',         link: '/de/explanation/field-trial-methodology' },
    ]}],
    '/de/reference/': [{ text: 'Referenz', items: [
      { text: 'Konfiguration',        link: '/de/reference/configuration' },
      { text: 'Framework-Module',     link: '/de/reference/framework-modules' },
      { text: 'REST API',             link: '/de/reference/api' },
    ]}],
  }
}

function sidebarPtBr() {
  return {
    '/pt-br/tutorials/': [{ text: 'Tutoriais', items: [
      { text: 'Primeiros passos',           link: '/pt-br/tutorials/getting-started' },
      { text: 'Implementar um domínio',     link: '/pt-br/tutorials/first-domain' },
    ]}],
    '/pt-br/how-to/': [
      { text: 'Começando', items: [
        { text: 'Novo projeto',                       link: '/pt-br/how-to/new-project' },
        { text: 'Adicionar novo domínio',             link: '/pt-br/how-to/add-new-domain' },
        { text: 'Implementar repositório SQLAlchemy', link: '/pt-br/how-to/sqlalchemy-repository' },
        { text: 'Configurar autenticação',            link: '/pt-br/how-to/configure-auth' },
        { text: 'Middleware de auth personalizado',   link: '/pt-br/how-to/custom-auth-middleware' },
        { text: 'Configurar MCP',                     link: '/pt-br/howto/mcp-setup' },
      ]},
      { text: 'Padrões', items: [
        { text: 'Padrões de resposta',     link: '/pt-br/how-to/response-patterns' },
        { text: 'Erros de validação',      link: '/pt-br/how-to/validation' },
        { text: 'RFC 9457 Problem Details',link: '/pt-br/how-to/problem-details' },
        { text: 'Injeção de dependência',  link: '/pt-br/how-to/dependency-injection' },
        { text: 'Pilha de middleware',     link: '/pt-br/how-to/middleware-stack' },
        { text: 'Lifespan & app.state',    link: '/pt-br/how-to/lifespan-and-app-state' },
        { text: 'UseCase assíncrono',      link: '/pt-br/how-to/async-use-case' },
        { text: 'Padrões de concorrência', link: '/pt-br/how-to/concurrency-patterns' },
        { text: 'Tarefas em background',   link: '/pt-br/how-to/background-tasks' },
        { text: 'Eventos de domínio',      link: '/pt-br/how-to/domain-events' },
        { text: 'Soft delete',             link: '/pt-br/how-to/soft-delete' },
        { text: 'Versionamento de API',    link: '/pt-br/how-to/api-versioning' },
        { text: 'CORS',                    link: '/pt-br/how-to/cors' },
      ]},
      { text: 'E/S, dados & entrada', items: [
        { text: 'Upload de arquivo',          link: '/pt-br/how-to/file-upload' },
        { text: 'Respostas em streaming',     link: '/pt-br/how-to/streaming' },
        { text: 'Logging estruturado',        link: '/pt-br/how-to/structured-logging' },
        { text: 'Webhook & HMAC',             link: '/pt-br/how-to/webhook' },
        { text: 'Decimal & entrada Unicode',  link: '/pt-br/how-to/decimal-unicode-input' },
        { text: 'Parsear e-mails',            link: '/pt-br/how-to/email-address-parsing' },
      ]},
      { text: 'Testes & publicação', items: [
        { text: 'Executar testes',           link: '/pt-br/how-to/run-tests' },
        { text: 'Testes com BD real',        link: '/pt-br/how-to/run-integration-tests' },
        { text: 'Publicar no PyPI',          link: '/pt-br/how-to/release-and-publish' },
      ]},
    ],
    '/pt-br/explanation/': [{ text: 'Explicações', items: [
      { text: 'Visão geral da arquitetura',    link: '/pt-br/explanation/architecture' },
      { text: 'Filosofia de design',           link: '/pt-br/explanation/design-philosophy' },
      { text: 'Um UseCase, duas superfícies',  link: '/pt-br/explanation/one-usecase-two-surfaces' },
      { text: 'Metodologia de Field Trial',    link: '/pt-br/explanation/field-trial-methodology' },
    ]}],
    '/pt-br/reference/': [{ text: 'Referência', items: [
      { text: 'Configuração',      link: '/pt-br/reference/configuration' },
      { text: 'Módulos do framework',link: '/pt-br/reference/framework-modules' },
      { text: 'REST API',          link: '/pt-br/reference/api' },
    ]}],
  }
}

function navEn() {
  return [
    { text: 'Tutorial',     link: '/tutorials/getting-started', activeMatch: '/tutorials/' },
    { text: 'How-to',       link: '/how-to/add-new-domain',     activeMatch: '/how-to/' },
    { text: 'Explanation',  link: '/explanation/architecture',  activeMatch: '/explanation/' },
    { text: 'Reference',    link: '/reference/configuration',   activeMatch: '/reference/' },
    {
      text: 'v1.0.0',
      items: [
        { text: 'Changelog',   link: 'https://github.com/hideyukiMORI/nene2-python/blob/main/CHANGELOG.md' },
        { text: 'Releases',    link: 'https://github.com/hideyukiMORI/nene2-python/releases' },
        { text: 'PHP NENE2',   link: 'https://hideyukimori.github.io/NENE2/' },
      ],
    },
  ]
}

function navJa() {
  return [
    { text: 'チュートリアル', link: '/ja/tutorials/getting-started', activeMatch: '/ja/tutorials/' },
    { text: 'ハウツー',       link: '/ja/how-to/add-new-domain',     activeMatch: '/ja/how-to/' },
    { text: '解説',           link: '/ja/explanation/architecture',  activeMatch: '/ja/explanation/' },
    { text: 'リファレンス',   link: '/ja/reference/configuration',   activeMatch: '/ja/reference/' },
    {
      text: 'v1.0.0',
      items: [
        { text: '変更履歴',  link: 'https://github.com/hideyukiMORI/nene2-python/blob/main/CHANGELOG.md' },
        { text: 'リリース', link: 'https://github.com/hideyukiMORI/nene2-python/releases' },
        { text: 'PHP NENE2', link: 'https://hideyukimori.github.io/NENE2/' },
      ],
    },
  ]
}

function sidebarEn() {
  return {
    '/tutorials/': [{
      text: 'Tutorials',
      items: [
        { text: 'Getting started',        link: '/tutorials/getting-started' },
        { text: 'Implement a new domain', link: '/tutorials/first-domain' },
      ],
    }],
    '/how-to/': [{
      text: 'Getting things done',
      items: [
        { text: 'Start a new project',           link: '/how-to/new-project' },
        { text: 'Add a new domain',              link: '/how-to/add-new-domain' },
        { text: 'Implement a SQLAlchemy repository', link: '/how-to/sqlalchemy-repository' },
        { text: 'Configure auth',                link: '/how-to/configure-auth' },
        { text: 'Custom auth middleware',        link: '/how-to/custom-auth-middleware' },
        { text: 'Set up MCP',                    link: '/howto/mcp-setup' },
      ],
    }, {
      text: 'Patterns',
      items: [
        { text: 'Response patterns',             link: '/how-to/response-patterns' },
        { text: 'Handle validation errors',      link: '/how-to/validation' },
        { text: 'RFC 9457 Problem Details',      link: '/how-to/problem-details' },
        { text: 'Dependency injection (Depends)', link: '/how-to/dependency-injection' },
        { text: 'Middleware stack ordering',     link: '/how-to/middleware-stack' },
        { text: 'Lifespan & app.state',          link: '/how-to/lifespan-and-app-state' },
        { text: 'Async use cases',               link: '/how-to/async-use-case' },
        { text: 'Concurrency patterns',          link: '/how-to/concurrency-patterns' },
        { text: 'Background tasks',              link: '/how-to/background-tasks' },
        { text: 'Domain events',                 link: '/how-to/domain-events' },
        { text: 'Soft delete',                   link: '/how-to/soft-delete' },
        { text: 'API versioning',                link: '/how-to/api-versioning' },
        { text: 'CORS',                          link: '/how-to/cors' },
      ],
    }, {
      text: 'I/O, data & input',
      items: [
        { text: 'File upload',                   link: '/how-to/file-upload' },
        { text: 'Streaming responses',           link: '/how-to/streaming' },
        { text: 'Structured logging',            link: '/how-to/structured-logging' },
        { text: 'Webhook & HMAC verification',   link: '/how-to/webhook' },
        { text: 'Decimal & Unicode input',       link: '/how-to/decimal-unicode-input' },
        { text: 'Parse email addresses',         link: '/how-to/email-address-parsing' },
      ],
    }, {
      text: 'Testing & release',
      items: [
        { text: 'Run tests',                     link: '/how-to/run-tests' },
        { text: 'Run real-DB integration tests', link: '/how-to/run-integration-tests' },
        { text: 'Release and publish to PyPI',   link: '/how-to/release-and-publish' },
      ],
    }],
    '/explanation/': [{
      text: 'Explanation',
      items: [
        { text: 'Architecture',      link: '/explanation/architecture' },
        { text: 'Design philosophy', link: '/explanation/design-philosophy' },
        { text: 'One UseCase, two surfaces (HTTP + MCP)', link: '/explanation/one-usecase-two-surfaces' },
        { text: 'Field Trial methodology', link: '/explanation/field-trial-methodology' },
      ],
    }, {
      text: 'ADR',
      collapsed: true,
      items: [
        { text: 'ADR-0001 Toolchain',         link: '/adr/0001-toolchain' },
        { text: 'ADR-0002 Clean Architecture', link: '/adr/0002-clean-architecture' },
        { text: 'ADR-0003 Security First',     link: '/adr/0003-security-first' },
        { text: 'ADR-0004 AI First',           link: '/adr/0004-ai-first-design' },
        { text: 'ADR-0005 Logging',            link: '/adr/0005-logging' },
        { text: 'ADR-0006 Rate Limiting',      link: '/adr/0006-rate-limiting' },
        { text: 'ADR-0009 MCP Design',         link: '/adr/0009-mcp-design' },
        { text: 'ADR-0010 AsyncUseCase',       link: '/adr/0010-async-use-case' },
      ],
    }],
    '/reference/': [{
      text: 'Reference',
      items: [
        { text: 'Configuration',     link: '/reference/configuration' },
        { text: 'Framework modules', link: '/reference/framework-modules' },
        { text: 'REST API',          link: '/reference/api' },
      ],
    }],
    '/adr/': [{
      text: 'Architecture Decision Records',
      items: [
        { text: 'ADR-0001 Toolchain',         link: '/adr/0001-toolchain' },
        { text: 'ADR-0002 Clean Architecture', link: '/adr/0002-clean-architecture' },
        { text: 'ADR-0003 Security First',     link: '/adr/0003-security-first' },
        { text: 'ADR-0004 AI First',           link: '/adr/0004-ai-first-design' },
        { text: 'ADR-0005 Logging',            link: '/adr/0005-logging' },
        { text: 'ADR-0006 Rate Limiting',      link: '/adr/0006-rate-limiting' },
        { text: 'ADR-0009 MCP Design',         link: '/adr/0009-mcp-design' },
        { text: 'ADR-0010 AsyncUseCase',       link: '/adr/0010-async-use-case' },
      ],
    }],
  }
}

function sidebarJa() {
  return {
    '/ja/tutorials/': [{
      text: 'チュートリアル',
      items: [
        { text: 'はじめての nene2-python', link: '/ja/tutorials/getting-started' },
        { text: '新しいドメインを実装する', link: '/ja/tutorials/first-domain' },
      ],
    }],
    '/ja/how-to/': [{
      text: '基本',
      items: [
        { text: '新しいプロジェクトを始める',          link: '/ja/how-to/new-project' },
        { text: '新しいドメインを追加する',            link: '/ja/how-to/add-new-domain' },
        { text: 'SQLAlchemy リポジトリを実装する',    link: '/ja/how-to/sqlalchemy-repository' },
        { text: '認証を設定する',                     link: '/ja/how-to/configure-auth' },
        { text: 'カスタム認証ミドルウェア',           link: '/ja/how-to/custom-auth-middleware' },
        { text: 'MCP セットアップ',                   link: '/ja/howto/mcp-setup' },
      ],
    }, {
      text: 'パターン',
      items: [
        { text: 'レスポンスパターン',                 link: '/ja/how-to/response-patterns' },
        { text: 'バリデーションエラーを扱う',         link: '/ja/how-to/validation' },
        { text: 'RFC 9457 Problem Details',           link: '/ja/how-to/problem-details' },
        { text: 'FastAPI Depends パターン',           link: '/ja/how-to/dependency-injection' },
        { text: 'ミドルウェアスタックの設定',         link: '/ja/how-to/middleware-stack' },
        { text: 'Lifespan と app.state',              link: '/ja/how-to/lifespan-and-app-state' },
        { text: 'AsyncUseCase と FastAPI の統合',     link: '/ja/how-to/async-use-case' },
        { text: '並行処理パターンの選び方',           link: '/ja/how-to/concurrency-patterns' },
        { text: 'BackgroundTasks',                    link: '/ja/how-to/background-tasks' },
        { text: 'ドメインイベントパターン',           link: '/ja/how-to/domain-events' },
        { text: 'ソフトデリート（論理削除）',         link: '/ja/how-to/soft-delete' },
        { text: 'API バージョニング',                 link: '/ja/how-to/api-versioning' },
        { text: 'CORS 設定',                          link: '/ja/how-to/cors' },
      ],
    }, {
      text: 'I/O・データ・入力',
      items: [
        { text: 'ファイルアップロード',               link: '/ja/how-to/file-upload' },
        { text: 'ストリーミングレスポンス',           link: '/ja/how-to/streaming' },
        { text: '構造化ログ（structlog）',            link: '/ja/how-to/structured-logging' },
        { text: 'Webhook と HMAC 署名検証',           link: '/ja/how-to/webhook' },
        { text: 'decimal と Unicode 数字入力',        link: '/ja/how-to/decimal-unicode-input' },
        { text: 'メールアドレスのパース',             link: '/ja/how-to/email-address-parsing' },
      ],
    }, {
      text: 'テスト・リリース',
      items: [
        { text: 'テストを実行する',                   link: '/ja/how-to/run-tests' },
        { text: '実DB統合テストの実行',               link: '/ja/how-to/run-integration-tests' },
        { text: 'リリースと PyPI 公開',               link: '/ja/how-to/release-and-publish' },
      ],
    }],
    '/ja/explanation/': [{
      text: '解説',
      items: [
        { text: 'アーキテクチャ概要',        link: '/ja/explanation/architecture' },
        { text: '設計思想と PHP との対応',   link: '/ja/explanation/design-philosophy' },
        { text: '1 つの UseCase、2 つのサーフェス（HTTP + MCP）', link: '/ja/explanation/one-usecase-two-surfaces' },
        { text: 'フィールドトライアル方法論', link: '/ja/explanation/field-trial-methodology' },
      ],
    }],
    '/ja/reference/': [{
      text: 'リファレンス',
      items: [
        { text: '設定リファレンス',             link: '/ja/reference/configuration' },
        { text: 'フレームワークモジュール',     link: '/ja/reference/framework-modules' },
        { text: 'REST API',                     link: '/ja/reference/api' },
      ],
    }],
  }
}

export default defineConfig({
  title: 'NENE2 Python',
  description: 'FastAPI + Clean Architecture + MCP. Python 3.12+. AI-ready from day one.',
  // Served at the root of the custom domain docs.nene2-python.dev (see docs/public/CNAME).
  base: '/',
  srcDir: './docs',
  outDir: './.vitepress/dist',
  cleanUrls: true,
  // Dead-link detection is ON so the build (docs.yml) fails on broken internal links.
  // Exceptions:
  // 1. FT INDEX.md — file exists and 200 on live site; VitePress lowercases path → false positive.
  // 2. Translated locales (fr/zh/de/pt-br) linking to EN-only directories (adr/, field-trials/,
  //    templates/, todo/) — these resources are not translated and VitePress can't follow the
  //    relative path across locale boundaries. The links are valid conceptually (they lead to the
  //    English source) but aren't resolvable within the locale subtree.
  ignoreDeadLinks: [
    /\/field-trials\/index/i,
    // Translated locales link to EN-only dirs (adr/, field-trials/, templates/, todo/) via
    // relative paths like ./../adr/... — these resolve outside the locale subtree and are
    // not translatable resources. Suppress rather than break the multilingual build.
    /\.\.\/adr\//,
    /\.\.\/field-trials\//,
    /\.\.\/templates\//,
    /\.\.\/todo\//,
  ],

  head: [
    ['meta', { name: 'theme-color', content: '#ffd43b' }],
    ['link', { rel: 'icon', href: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🐍</text></svg>' }],
  ],

  locales: {
    root: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: navEn(),
        sidebar: sidebarEn(),
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: 'Edit this page on GitHub',
        },
        footer: {
          message: 'Released under the MIT License.',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
      },
    },
    ja: {
      label: '日本語',
      lang: 'ja',
      themeConfig: {
        nav: navJa(),
        sidebar: sidebarJa(),
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: 'GitHub でこのページを編集',
        },
        footer: {
          message: 'MIT ライセンスの下でリリースされています。',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
      },
    },
    fr: {
      label: 'Français',
      lang: 'fr',
      themeConfig: {
        nav: navFr(),
        sidebar: sidebarFr(),
        editLink: { pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path', text: 'Éditer cette page sur GitHub' },
        footer: { message: 'Publié sous la licence MIT.', copyright: 'Copyright © 2026 hideyukiMORI' },
      },
    },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      themeConfig: {
        nav: navZh(),
        sidebar: sidebarZh(),
        editLink: { pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path', text: '在 GitHub 上编辑此页面' },
        footer: { message: '根据 MIT 许可证发布。', copyright: 'Copyright © 2026 hideyukiMORI' },
      },
    },
    'pt-br': {
      label: 'Português (Brasil)',
      lang: 'pt-BR',
      themeConfig: {
        nav: navPtBr(),
        sidebar: sidebarPtBr(),
        editLink: { pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path', text: 'Editar esta página no GitHub' },
        footer: { message: 'Lançado sob a Licença MIT.', copyright: 'Copyright © 2026 hideyukiMORI' },
      },
    },
    de: {
      label: 'Deutsch',
      lang: 'de',
      themeConfig: {
        nav: navDe(),
        sidebar: sidebarDe(),
        editLink: { pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path', text: 'Diese Seite auf GitHub bearbeiten' },
        footer: { message: 'Veröffentlicht unter der MIT-Lizenz.', copyright: 'Copyright © 2026 hideyukiMORI' },
      },
    },
  },

  themeConfig: {
    siteTitle: '🐍 NENE2',
    socialLinks: [
      { icon: 'github', link: 'https://github.com/hideyukiMORI/nene2-python' },
    ],
    search: { provider: 'local' },
    outline: { level: [2, 3] },
  },

  markdown: {
    theme: { light: 'github-light', dark: 'one-dark-pro' },
    lineNumbers: true,
  },
})
