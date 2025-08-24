# 🔒 Tetheritall Security Guidelines

## Overview
This document outlines security best practices and guidelines for the Tetheritall project to prevent credential exposure and maintain security standards.

## 🚨 Critical Security Rules

### 1. Never Commit Secrets
- **NEVER** commit passwords, API keys, or database credentials to version control
- **NEVER** commit `.env` files or any files containing secrets
- **ALWAYS** use environment variables for sensitive configuration
- **ALWAYS** use placeholder values in example files

### 2. Environment Variables
```bash
# ✅ GOOD - Use environment variables
DATABASE_URL=postgresql://user:pass@host:port/db

# ❌ BAD - Hardcoded credentials
DATABASE_URL=postgresql://tetheritall_user:password@localhost:5432/tetheritall
```

### 3. File Naming Conventions
- Use `.template` or `.example` suffix for configuration templates
- Never use `.env` in example files
- Use descriptive names that indicate the file contains sensitive data

## 🛡️ Pre-commit Security Checks

### Automated Scanning
Before each commit, the following checks run automatically:

1. **Pre-commit Hook**: Scans for common secret patterns
2. **GitHub Actions**: Runs multiple security scanners
3. **Local Security Script**: PowerShell script for manual scanning

### Manual Security Scan
```powershell
# Run the security scanner
.\scripts\security-scan.ps1

# Run with verbose output
.\scripts\security-scan.ps1 -Verbose

# Run with auto-fix (when available)
.\scripts\security-scan.ps1 -Fix
```

## 🔍 Security Scanning Tools

### 1. Bandit (Python Security Linter)
```bash
pip install bandit
bandit -r . -f json -o bandit-report.json
```

### 2. Safety (Dependency Vulnerability Scanner)
```bash
pip install safety
safety check --json --output safety-report.json
```

### 3. Detect Secrets
```bash
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline
```

### 4. TruffleHog (Secrets Scanner)
```bash
docker run --rm -v "$PWD:/pwd" trufflesecurity/trufflehog:latest --only-verified
```

## 📋 Security Checklist

### Before Committing Code
- [ ] Run `.\scripts\security-scan.ps1`
- [ ] Check for hardcoded credentials
- [ ] Verify `.env` files are in `.gitignore`
- [ ] Review any new configuration files
- [ ] Check for exposed API keys or tokens

### Before Pushing to GitHub
- [ ] Ensure no secrets in commit history
- [ ] Verify environment variables are used
- [ ] Check that example files use placeholders
- [ ] Review GitHub Actions security scan results

### Before Deploying
- [ ] Rotate any exposed credentials
- [ ] Verify production secrets are in secure storage
- [ ] Check security scan reports
- [ ] Review access permissions

## 🔧 Environment Setup

### 1. Create Environment File
```bash
# Copy the template
cp env.template .env

# Edit with your actual values
notepad .env
```

### 2. Verify .gitignore
Ensure `.env` files are in `.gitignore`:
```gitignore
# Security & Credentials
*.env
.env.*
.env.local
.env.development
.env.test
.env.production
```

### 3. Test Configuration
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Test database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL not found in environment variables")
```

## 🚨 Incident Response

### If Credentials Are Exposed

1. **Immediate Actions**
   - Rotate all exposed credentials immediately
   - Remove credentials from codebase
   - Clean git history using `git-filter-repo`
   - Force push cleaned history to GitHub

2. **Investigation**
   - Determine scope of exposure
   - Check if credentials were used
   - Review access logs
   - Identify root cause

3. **Prevention**
   - Update security procedures
   - Enhance scanning tools
   - Train team members
   - Implement additional safeguards

### Git History Cleanup
```bash
# Install git-filter-repo
pip install git-filter-repo

# Create list of credentials to remove
echo "wk7XLV6dVdYRZ9EJJ3TLVA" > credentials-to-remove.txt

# Clean history
git filter-repo --replace-text credentials-to-remove.txt --force

# Re-add remote and force push
git remote add origin https://github.com/TethralAI/Tetheritall.git
git push origin main --force
```

## 🔐 Secure Development Practices

### 1. Code Review
- Always review code for security issues
- Check for hardcoded credentials
- Verify proper use of environment variables
- Review third-party dependencies

### 2. Dependency Management
- Regularly update dependencies
- Use security scanning tools
- Monitor for known vulnerabilities
- Use dependency pinning

### 3. Access Control
- Use least privilege principle
- Implement proper authentication
- Use role-based access control
- Regular access reviews

### 4. Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for data in transit
- Implement proper session management
- Follow data retention policies

## 📚 Additional Resources

### Security Tools
- [OWASP Security Guidelines](https://owasp.org/)
- [GitHub Security Best Practices](https://docs.github.com/en/github/managing-security-vulnerabilities)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-learning/)

### Monitoring
- [GitGuardian](https://www.gitguardian.com/) - Secret detection
- [Snyk](https://snyk.io/) - Vulnerability scanning
- [TruffleHog](https://github.com/trufflesecurity/trufflehog) - Secret scanning

### Training
- Regular security training for team members
- Code review guidelines
- Incident response procedures
- Security awareness programs

## 📞 Security Contacts

### Emergency Contacts
- **Security Team**: security@tetheritall.com
- **DevOps Team**: devops@tetheritall.com
- **Infrastructure Team**: infra@tetheritall.com

### Reporting Security Issues
- Use GitHub Security Advisories
- Email security@tetheritall.com
- Follow incident response procedures
- Document all security incidents

---

**Remember**: Security is everyone's responsibility. When in doubt, ask for help rather than making assumptions about security practices.
