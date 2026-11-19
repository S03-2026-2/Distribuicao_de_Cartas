# Separadas porque pedem reações diferentes: indisponibilidade justifica reentrega,
# rejeição indica mensagem fora do contrato e repetir não resolve.
class BrokerIndisponivelError(ConnectionError):
    pass


class MensagemRejeitadaPeloBrokerError(RuntimeError):
    pass
