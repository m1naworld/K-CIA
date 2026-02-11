import type { Config } from "tailwindcss";

const config: Config = {
	darkMode: ["class"],
	content: [
		"./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/components/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/app/**/*.{js,ts,jsx,tsx,mdx}",
	],
	theme: {
		extend: {
			colors: {
				// Red Spectrum
				'pure-red': '#FF0000',
				'scarlet': '#FF2400',
				'crimson': '#BD2E4A',
				'ruby': '#E11F51',
				'coral-red': '#E44327',
				'terracotta': '#E2725B',
				'rose-red': '#C21E56',
				'oxblood': '#4A0404',
				'claret': '#7F1734',
				'sangria': '#9C1F4B',
				'salmon': '#FA8072',
				'blush': '#F9C0C4',
				'marsala': '#964F4C',
				'grenadine': '#DC4C46',
				'goji-berry': '#CC142F',

				// Orange Spectrum
				'pure-orange': '#FFA500',
				'tangerine': '#F28500',
				'ochre': '#CC7722',
				'apricot': '#FFB27F',
				'persimmon': '#EC5800',
				'pumpkin': '#FF7518',
				'rust': '#B7410E',
				'copper': '#B87333',
				'burnt-orange': '#CC5500',
				'peach-puff': '#FFDAB9',
				'coral-blush': '#F88379',
				'creamsicle': '#FFD7A0',
				'living-coral': '#FF6F61',
				'flame': '#F2552C',
				'chili-oil': '#944537',

				// Yellow Spectrum
				'lemon-yellow': '#FFF44F',
				'goldenrod': '#DAA520',
				'amber': '#FFBF00',
				'mustard-yellow': '#FFCE1B',
				'wheat': '#F5DEB3',
				'flax': '#EEDC82',
				'ochre-yellow': '#CB9D06',
				'bronze-gold': '#A97132',
				'naples-yellow': '#FADA5E',
				'cornsilk': '#FFF8DC',
				'buttercream': '#F3E5AB',
				'illuminating': '#F5DF4D',
				'honey-gold': '#DDB67D',
				'autumn-blaze': '#D1933F',

				// Green Spectrum
				'emerald-green': '#50C878',
				'kelly-green': '#4CBB17',
				'olive-green': '#708238',
				'moss-green': '#8A9A5B',
				'fern-green': '#4F7942',
				'forest-green': '#27503D',
				'hunter-green': '#355E3B',
				'bottle-green': '#006A4E',
				'mint-green': '#98FF98',
				'celadon': '#ACE1AF',
				'greenery': '#88B04B',

				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))'
				},
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				chart: {
					'1': 'hsl(var(--chart-1))',
					'2': 'hsl(var(--chart-2))',
					'3': 'hsl(var(--chart-3))',
					'4': 'hsl(var(--chart-4))',
					'5': 'hsl(var(--chart-5))'
				}
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
};
export default config;
