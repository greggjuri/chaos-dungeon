# Chaos Dungeon

A text-based RPG web game where Claude serves as an intelligent Dungeon Master, using D&D 1983 BECMI rules.

**Live at**: [chaos.jurigregg.com](https://chaos.jurigregg.com) (coming soon)

## Features

- 🎭 AI Dungeon Master powered by Claude
- ⚔️ Classic D&D BECMI rules (1983 revision)
- 🎲 Real dice mechanics with d20 system
- 💾 Save and resume your adventures
- 🌙 Mature, dark fantasy content

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.12+
- AWS CLI configured
- AWS CDK CLI (`npm install -g aws-cdk`)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/greggjuri/chaos-dungeon
cd chaos-dungeon

# Backend (Lambdas)
cd lambdas
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run dev

# Infrastructure
cd ../cdk
pip install -r requirements.txt
cdk synth
```

### Deploy to AWS

```bash
cd cdk
cdk deploy --all
```

## Project Structure

```
chaos-dungeon/
├── CLAUDE.md           # AI coding assistant instructions
├── docs/               # Documentation
│   ├── PLANNING.md     # Architecture and design
│   ├── TASK.md         # Current tasks
│   └── DECISIONS.md    # Architecture decisions
├── initials/           # Feature specifications
├── prps/               # Implementation plans
├── cdk/                # AWS CDK infrastructure
├── lambdas/            # Python Lambda functions
├── frontend/           # React application
└── examples/           # Code patterns
```

## Architecture

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: AWS Lambda + API Gateway
- **Database**: DynamoDB (single-table design)
- **AI**: Claude API (Haiku 3)
- **Hosting**: S3 + CloudFront

## Game System

Based on D&D Basic/Expert/Companion/Master rules (1983):

- **Classes**: Fighter, Thief, Magic-User, Cleric
- **Levels**: 1-36 (Basic through Master)
- **Combat**: d20 + modifiers vs Armor Class
- **Magic**: Vancian spell system

## Cost

Designed to run under $20/month on AWS:
- Claude Haiku 3: ~$10-15/month
- AWS Services: ~$5-10/month

## Contributing

This is a personal project, but suggestions are welcome!

## License

MIT

---

*Built with chaos, powered by Claude* 🐉
