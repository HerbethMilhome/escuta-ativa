# Comandos Rápidos - Interview Assistant

## Ativar ambiente virtual
```bash
cd C:\Projetos\entrevista
venv\Scripts\activate
```

## Rodar com Ollama (gratuito)
```bash
python main.py --context "Dev Java Senior, 10 anos, Spring Boot, Angular, React, Docker"
python main.py --context "Meu nome é Herbeth Milhome, desenvolvedor Java sênior com 10 anos de experiência, formado em Análise e Desenvolvimento de Sistemas. Atualmente Desenvolvedor Sênior no Grupo Pulsati (desde fev/2022), alocado na MV — empresa de transformação digital na área da saúde — onde atuo com Java, Spring Boot, Hibernate, Oracle, SQL, JUnit, mockito, Angular e Jasper Reports, contribuindo com correção de bugs críticos, refatorações e desenvolvimento de novas funcionalidades. Experiências anteriores: Datainfo (alocado na Philips, framework Tasy, 1 ano), Grupo Portfolio (alocado na Unimed, 3,5 anos), Scio Soluções (1,5 anos). Stack principal: Java 5-8, Spring Boot, Spring Framework, Angular, Kotlin, Oracle, PostgreSQL, Hibernate, API REST, Docker, Jenkins, Maven, Git, PL/SQL, JSF, JasperReports, SOLID, Clean Code, CI/CD. Tenho perfil full-stack com foco em back-end, experiência sólida no setor de saúde (MV, Philips, Unimed), facilidade para integração em equipes e foco em melhoria contínua. Busco posição de desenvolvedor sênior Java em times que valorizem qualidade de código e impacto real no produto."
```

## Rodar com Claude API (pago ~$0.005/pergunta)
```bash
python main.py --provider claude --context "Dev Java Senior, 10 anos, Spring Boot, Angular"
```
Requer arquivo `.env` com `ANTHROPIC_API_KEY=sk-ant-sua-chave`

## Rodar com modelo Ollama diferente
```bash
python main.py --ollama-model mistral --context "Dev Java Senior, 8 anos, Spring Boot, Angular"
```

## Entrevista em inglês
```bash
python main.py --language en --context "Java Senior Dev, 10 years, Spring Boot, Angular"
python main.py --context "My name is Herbeth Milhome, a senior Java developer with 10 years of experience, holding a degree in Systems Analysis and Development. Currently working as Senior Developer at Grupo Pulsati (since Feb/2022), allocated at MV — a digital transformation company in the healthcare sector — where I work with Java, Spring Boot, Hibernate, Oracle, SQL, JUnit, Mockito, Angular, and Jasper Reports, contributing with critical bug fixes, refactoring, and new feature development. Previous experience: Datainfo (allocated at Philips, Tasy framework, 1 year), Grupo Portfolio (allocated at Unimed, 3.5 years), Scio Soluções (1.5 years). Main stack: Java 5-8, Spring Boot, Spring Framework, Angular, Kotlin, Oracle, PostgreSQL, Hibernate, REST APIs, Docker, Jenkins, Maven, Git, PL/SQL, JSF, JasperReports, SOLID, Clean Code, CI/CD. I have a full-stack profile with a strong back-end focus, solid experience in the healthcare sector (MV, Philips, Unimed), strong team integration skills, and a continuous improvement mindset. I am seeking a senior Java developer position in teams that value code quality and real product impact."
```

## Transcrição mais precisa (mais lenta)
```bash
python main.py --model small --context "Dev Java Senior, 8 anos, Spring Boot, Angular"
```

## Ajustar sensibilidade
```bash
# Silêncio mais curto (1.5s) e mais sensível ao som
python main.py --silence 1.5 --threshold 0.005 --context "Dev Java Senior, 8 anos, Spring Boot, Angular"
```

## Instalar dependências (só na primeira vez)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.1
```
