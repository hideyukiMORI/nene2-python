import { defineConfig } from 'vitepress'

function nav() {
  return [
    { text: 'Tutorial',     link: '/tutorials/getting-started', activeMatch: 'tutorials/' },
    { text: 'How-to',       link: '/how-to/add-new-domain',     activeMatch: 'how-to/' },
    { text: 'Explanation',  link: '/explanation/architecture',  activeMatch: 'explanation/' },
    { text: 'Reference',    link: '/reference/configuration',   activeMatch: 'reference/' },
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

function sidebar() {
  return {
    '/tutorials/': [{
      text: 'Tutorials',
      items: [
        { text: 'Getting started',       link: '/tutorials/getting-started' },
        { text: 'Implement a new domain', link: '/tutorials/first-domain' },
      ],
    }],
    '/how-to/': [{
      text: 'How-to guides',
      items: [
        { text: 'Add a new domain',  link: '/how-to/add-new-domain' },
        { text: 'Configure auth',    link: '/how-to/configure-auth' },
        { text: 'Set up MCP',        link: '/howto/mcp-setup' },
        { text: 'Run tests',         link: '/how-to/run-tests' },
      ],
    }],
    '/explanation/': [{
      text: 'Explanation',
      items: [
        { text: 'Architecture',       link: '/explanation/architecture' },
        { text: 'Design philosophy',  link: '/explanation/design-philosophy' },
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
        { text: 'Configuration',          link: '/reference/configuration' },
        { text: 'Framework modules',      link: '/reference/framework-modules' },
        { text: 'REST API',               link: '/reference/api' },
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

  themeConfig: {
    siteTitle: '🐍 NENE2',
    nav: nav(),
    sidebar: sidebar(),

    socialLinks: [
      { icon: 'github', link: 'https://github.com/hideyukiMORI/nene2-python' },
    ],

    search: { provider: 'local' },
    outline: { level: [2, 3] },

    editLink: {
      pattern: 'https://github.com/hideyukiMORI/nene2-python/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2026 hideyukiMORI',
    },
  },

  markdown: {
    theme: { light: 'github-light', dark: 'one-dark-pro' },
    lineNumbers: true,
  },
})
