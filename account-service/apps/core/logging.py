import logging
import re


class PIIScrubFilter(logging.Filter):
    PII_FIELDS = {'password', 'token', 'access', 'refresh', 'email', 'authorization'}
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.EMAIL_PATTERN.sub('[email]', record.msg)

        for field in self.PII_FIELDS:
            if hasattr(record, field):
                setattr(record, field, '***')

        return True
