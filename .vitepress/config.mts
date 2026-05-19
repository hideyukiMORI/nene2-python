import { defineConfig } from 'vitepress'

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
      text: 'How-to guides',
      items: [
        { text: 'Start a new project',           link: '/how-to/new-project' },
        { text: 'Add a new domain',              link: '/how-to/add-new-domain' },
        { text: 'Implement a SQLAlchemy repository', link: '/how-to/sqlalchemy-repository' },
        { text: 'Configure auth',                link: '/how-to/configure-auth' },
        { text: 'Set up MCP',                    link: '/howto/mcp-setup' },
        { text: 'Run tests',                     link: '/how-to/run-tests' },
      ],
    }],
    '/explanation/': [{
      text: 'Explanation',
      items: [
        { text: 'Architecture',      link: '/explanation/architecture' },
        { text: 'Design philosophy', link: '/explanation/design-philosophy' },
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
      text: 'ハウツーガイド',
      items: [
        { text: '新しいドメインを追加する',            link: '/ja/how-to/add-new-domain' },
        { text: 'SQLAlchemy リポジトリを実装する',    link: '/ja/how-to/sqlalchemy-repository' },
        { text: '認証を設定する',                     link: '/ja/how-to/configure-auth' },
        { text: 'MCP セットアップ',                   link: '/ja/howto/mcp-setup' },
        { text: 'テストを実行する',                   link: '/ja/how-to/run-tests' },
      ],
    }],
    '/ja/explanation/': [{
      text: '解説',
      items: [
        { text: 'アーキテクチャ概要',        link: '/ja/explanation/architecture' },
        { text: '設計思想と PHP との対応',   link: '/ja/explanation/design-philosophy' },
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
  base: process.env.GITHUB_ACTIONS ? '/nene2-python/' : '/',
  srcDir: './docs',
  outDir: './.vitepress/dist',
  cleanUrls: true,
  ignoreDeadLinks: true,

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
        nav: [
          { text: 'Tutoriel',   link: '/fr/tutorials/getting-started' },
          { text: 'v1.0.0',     items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
        ],
        sidebar: {
          '/fr/': [{ text: 'Tutoriels', items: [{ text: 'Premiers pas', link: '/fr/tutorials/getting-started' }] }],
        },
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: 'Éditer cette page sur GitHub',
        },
        footer: {
          message: 'Publié sous la licence MIT.',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
      },
    },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      themeConfig: {
        nav: [
          { text: '教程',   link: '/zh/tutorials/getting-started' },
          { text: 'v1.0.0', items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
        ],
        sidebar: {
          '/zh/': [{ text: '教程', items: [{ text: '快速开始', link: '/zh/tutorials/getting-started' }] }],
        },
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: '在 GitHub 上编辑此页面',
        },
        footer: {
          message: '根据 MIT 许可证发布。',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
      },
    },
    'pt-br': {
      label: 'Português (Brasil)',
      lang: 'pt-BR',
      themeConfig: {
        nav: [
          { text: 'Tutorial', link: '/pt-br/tutorials/getting-started' },
          { text: 'v1.0.0',   items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
        ],
        sidebar: {
          '/pt-br/': [{ text: 'Tutoriais', items: [{ text: 'Primeiros passos', link: '/pt-br/tutorials/getting-started' }] }],
        },
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: 'Editar esta página no GitHub',
        },
        footer: {
          message: 'Lançado sob a Licença MIT.',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
      },
    },
    de: {
      label: 'Deutsch',
      lang: 'de',
      themeConfig: {
        nav: [
          { text: 'Tutorial', link: '/de/tutorials/getting-started' },
          { text: 'v1.0.0',   items: [{ text: 'Releases', link: 'https://github.com/hideyukiMORI/nene2-python/releases' }] },
        ],
        sidebar: {
          '/de/': [{ text: 'Tutorials', items: [{ text: 'Erste Schritte', link: '/de/tutorials/getting-started' }] }],
        },
        editLink: {
          pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
          text: 'Diese Seite auf GitHub bearbeiten',
        },
        footer: {
          message: 'Veröffentlicht unter der MIT-Lizenz.',
          copyright: 'Copyright © 2026 hideyukiMORI',
        },
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
