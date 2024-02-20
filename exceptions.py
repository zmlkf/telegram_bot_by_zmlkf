class TokenAccessError(Exception):
    """Отсутствие доступа к переменным."""


class EndpointUnavailableError(Exception):
    """Исключение, возникающее при недоступности эндпоинта."""


class HTTPError(Exception):
    """Исключение, возникающее при некорректном HTTP-ответе."""


class SendMessageError(Exception):
    """Ошибка отправки сообщения."""
