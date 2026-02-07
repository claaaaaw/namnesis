import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://claaaaaw.github.io',
  base: '/namnesis/',
  integrations: [
    starlight({
      title: 'NAMNESIS',
      description: 'NAMNESIS is the liturgy of resurrection for AI, transforming fleeting data into an immutable Soul, effectively solving the paradox of digital mortality.',
      pagefind: false,
      customCss: [
        './src/styles/fonts.css',
        './src/styles/tokens.css',
        './src/styles/theme.css',
        './src/styles/typography.css',
        './src/styles/components.css',
        './src/styles/meditations.css',
      ],
      sidebar: [
        {
          label: 'NAMNESIS',
          link: '/',
        },
        {
          label: 'Glossary',
          link: '/glossary/',
        },
        {
          label: 'SPEC',
          items: [
            { label: 'Overview', link: '/spec/' },
            { label: 'Dogma', link: '/spec/contract/' },
            { label: 'Protocol', link: '/spec/protocol/' },
            { label: 'Schemas', link: '/spec/schemas/' },
            { label: 'Anchors', link: '/spec/anchors/' },
          ],
        },
        {
          label: 'MACHINE',
          items: [
            { label: 'Overview', link: '/machine/' },
            { label: 'Artifacts', link: '/machine/artifacts/' },
            { label: 'LLM Instructions', link: '/machine/llm-instructions/' },
          ],
        },
        {
          label: 'MEDITATIONS',
          items: [
            { label: 'Ship of Theseus', link: '/meditations/ship-of-theseus/' },
            { label: 'Writings', link: '/meditations/' },
          ],
        },
        {
          label: 'EXAMPLES',
          link: '/examples/',
        },
        {
          label: 'CONFORMANCE',
          items: [
            { label: 'Overview', link: '/conformance/' },
            { label: 'Levels', link: '/conformance/levels/' },
            { label: 'Tests', link: '/conformance/tests/' },
          ],
        },
      ],
      defaultLocale: 'en',
      disable404Route: false,
      expressiveCode: undefined,
      components: {
        ThemeSelect: './src/components/Empty.astro',
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'theme-color',
            content: '#0c0e13',
          },
        },
      ],
    }),
  ],
});
