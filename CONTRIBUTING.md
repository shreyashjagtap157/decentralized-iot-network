# Contributing

Run basic setup:

```bash
# Smart contracts
cd smart-contracts
npm install
npm run compile

# Web dashboard
cd ../web-dashboard
npm install
npm run dev
```

Testing:

```bash
# Smart contracts
cd smart-contracts
npm test

# Backend
cd ../backend-services
pytest

# Frontend
cd ../web-dashboard
npm test
```

Husky hooks (after first install):

```bash
# run once after npm install
npx husky install
npx husky add .husky/pre-commit "npx lint-staged"
```

CI and code quality checks are defined in `.github/workflows/ci-cd.yml`.
