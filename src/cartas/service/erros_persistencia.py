class ConflitoDePersistenciaError(RuntimeError):
    """O estado persistido mudou desde que o chamador o leu.

    Faz parte do contrato dos repositórios: o chamador pode reler os dados e
    tentar a operação novamente.
    """
