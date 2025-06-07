# Security Guide (STDIO Edition)

This document outlines security best practices for MCP in STDIO mode.

## Security Model

- MCP is an internal-only tool—no network exposure, no open ports.
- All communication is via stdin/stdout (local subprocess).
- Plugins are executed as subprocesses and must not leak sensitive data.

## Deployment Security

- Run MCP only in trusted environments (e.g., inside Letta container).
- Ensure only trusted users can launch or interact with the daemon.
- Secure file permissions for all plugin scripts and config files.

## Plugin Security

- Validate all input in plugins.
- Never log or print sensitive data (API keys, tokens, etc.).
- Use environment variables for secrets.
- Handle errors gracefully and return only necessary error info.

## Logging & Auditing

- All requests and results are logged (excluding sensitive data).
- Regularly review logs for suspicious activity or errors.

## Incident Response

- If compromise is suspected, stop the daemon, rotate secrets, and review logs.
- Restore from backup if necessary.

## Compliance

### Data Protection

1. **Sensitive Data**
   - Identify sensitive data
   - Implement controls
   - Regular audits

2. **Retention**
   - Define retention periods
   - Secure deletion
   - Audit trails

### Access Control

1. **Authentication**
   - Strong passwords
   - Multi-factor auth
   - Session management

2. **Authorization**
   - Role-based access
   - Regular reviews
   - Access logs

## Security Checklist

### Deployment

- [ ] Deploy in private network
- [ ] Configure firewall rules
- [ ] Set up monitoring
- [ ] Enable audit logging
- [ ] Configure backups

### Configuration

- [ ] Use environment variables
- [ ] Set secure defaults
- [ ] Enable SSL/TLS
- [ ] Configure timeouts
- [ ] Set up rate limiting

### Maintenance

- [ ] Regular updates
- [ ] Security patches
- [ ] Log rotation
- [ ] Backup verification
- [ ] Access review

## Resources

- [OWASP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework) 