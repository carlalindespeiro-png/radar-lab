class QueryBuilder:
    def __init__(self):
        # Consultas más cortas, usando comillas para frases exactas y operadores de foro
        self.templates = [
            '"gestión de avisos" {sector} foro',
            '"software mantenimiento" {territorio} opiniones',
            '"coordinación de técnicos" {sector}',
            '"presupuestos" {sector} quejas',
            'inurl:foro "{sector}" {territorio}',
            '"parte de trabajo" {sector} software'
        ]

    def build_queries(self, sector_name: str, territory_name: str, max_queries: int = 6) -> list[str]:
        queries = []
        # Limpiamos el nombre del sector (quitamos "y" y "de" para que sea más corto)
        sector_clean = sector_name.lower().replace(" y ", " ").replace(" de ", " ")
        territory_clean = territory_name.lower()
        
        for template in self.templates:
            query = template.format(sector=sector_clean, territorio=territory_clean)
            queries.append(query)
            if len(queries) >= max_queries:
                break
        return queries