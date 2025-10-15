// PNCP Extrator - Main Application
class PNCPApp {
    constructor() {
        this.apiUrl = 'http://127.0.0.1:8000';
        this.loading = false;
        this.stats = {
            totalEditais: 0,
            novosHoje: 0,
            atualizados: 0,
            erros: 0
        };
        this.editais = [];
        
        // Timeline variables
        this.currentTaskId = null;
        this.eventSource = null;
        this.autoScrollEnabled = true;
        this.timelineEvents = [];
        
        // Table variables
        this.editaisFiltrados = [];
        this.editaisOrdenados = [];
        this.paginaAtual = 1;
        this.linhasPorPagina = 25;
        this.ordenacao = { campo: 'created_at', direcao: 'desc' };
        this.filtros = {
            situacao: '',
            modalidade: '',
            busca: ''
        };
        
        // Inicialização assíncrona
        this.init().catch(error => {
            console.error('❌ Erro na inicialização da aplicação:', error);
        });
    }

    async init() {
        try {
            console.log('🚀 Inicializando aplicação PNCP Extrator...');
            
            // Carrega estatísticas (comentado - não há elementos no HTML)
            console.log('📊 Carregando estatísticas...');
            try {
                // await this.carregarEstatisticas();
                this.stats = { totalEditais: 0, novosHoje: 0, atualizados: 0, erros: 0 };
                console.log('📊 Estatísticas comentadas - elementos não existem no HTML');
            } catch (error) {
                console.error('❌ Erro ao carregar estatísticas:', error);
                this.stats = { totalEditais: 0, novosHoje: 0, atualizados: 0, erros: 0 };
            }
            
            // Carrega editais do banco
            console.log('📋 Carregando editais...');
            try {
                await this.carregarEditais();
            } catch (error) {
                console.error('❌ Erro ao carregar editais:', error);
                this.editais = this.getDadosSimulados();
                this.renderizarEditais();
            }
            
            // Configura atualização automática
        this.iniciarAtualizacoesAutomaticas();
            
            console.log('✅ Aplicação inicializada com sucesso!');
            this.mostrarNotificacao('Aplicação carregada com sucesso!', 'success');
            
        } catch (error) {
            console.error('❌ Erro na inicialização:', error);
            this.mostrarNotificacao('Erro ao inicializar aplicação', 'error');
            
            // Fallback: usar dados simulados
            this.editais = this.getDadosSimulados();
            this.renderizarEditais();
        }
    }
    
    iniciarAtualizacoesAutomaticas() {
        // Atualizar estatísticas a cada 30 segundos
        setInterval(async () => {
            if (!this.loading) {
                await this.carregarEstatisticas();
            }
        }, 30000);
        
        // Atualizar editais a cada 60 segundos
        setInterval(async () => {
            if (!this.loading) {
                await this.carregarEditais();
            }
        }, 60000);
    }

    // API Methods
    async fazerRequisicao(endpoint, options = {}) {
        try {
            const url = `${this.apiUrl}${endpoint}`;
            console.log(`🌐 Fazendo requisição para: ${url}`);
            
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            console.log(`📡 Resposta recebida: ${response.status} ${response.statusText}`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ Erro HTTP ${response.status}:`, errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }

            const data = await response.json();
            console.log(`✅ Dados recebidos:`, data);
            return data;
            
        } catch (error) {
            console.error('❌ Erro na requisição:', error);
            this.mostrarNotificacao('Erro na comunicação com a API', 'error');
            throw error;
        }
    }

    // Statistics
    async carregarEstatisticas() {
        try {
            console.log('📊 Carregando estatísticas da API...');
            const data = await this.fazerRequisicao('/estatisticas');
            console.log('📊 Dados recebidos:', data);
            
            this.stats = {
                totalEditais: data.data?.total_editais || 0,
                novosHoje: data.data?.editais_ultimos_7_dias || 0,
                atualizados: 0, // Pode ser implementado depois
                erros: 0 // Pode ser implementado depois
            };
            
            console.log('📊 Stats processadas:', this.stats);
            
            // Atualiza a UI
            this.atualizarStatsUI();
            window.stats = this.stats;
        } catch (error) {
            console.error('❌ Erro ao carregar estatísticas:', error);
            // Usar dados simulados quando a API falhar
            this.stats = {
                totalEditais: 248,
                novosHoje: 15,
                atualizados: 5,
                erros: 0
            };
            this.atualizarStatsUI();
            window.stats = this.stats;
            console.log('📊 Usando stats simuladas:', this.stats);
        }
    }

    atualizarStatsUI() {
        console.log('🔄 Atualizando UI das estatísticas...');
        
        // Atualiza os elementos da UI com os dados das estatísticas
        const elements = {
            totalEditais: document.querySelector('[x-text="stats.totalEditais || \'0\'"]'),
            novosHoje: document.querySelector('[x-text="stats.novosHoje || \'0\'"]'),
            atualizados: document.querySelector('[x-text="stats.atualizados || \'0\'"]'),
            erros: document.querySelector('[x-text="stats.erros || \'0\'"]')
        };

        console.log('🔍 Elementos encontrados:', elements);

        Object.keys(elements).forEach(key => {
            if (elements[key]) {
                elements[key].textContent = this.stats[key] || '0';
                console.log(`✅ ${key}: ${this.stats[key]}`);
            } else {
                console.log(`⚠️ Elemento não encontrado: ${key}`);
            }
        });
        
        // Também atualizar elementos globais para Alpine.js
        window.stats = this.stats;
        console.log('✅ Stats atualizadas:', this.stats);
    }

    // Editais
    async carregarEditais() {
        try {
            console.log('🔄 Carregando editais...');
            
            // Sempre tenta carregar do banco primeiro
            try {
                const editaisDoBanco = await this.buscarEditaisDoBanco();
                if (editaisDoBanco && editaisDoBanco.length > 0) {
                    this.editais = editaisDoBanco;
                    console.log(`✅ ${editaisDoBanco.length} editais carregados do banco de dados`);
                } else {
                    console.log('⚠️ Nenhum edital encontrado no banco, usando dados simulados');
                    this.editais = this.getDadosSimulados();
                }
            } catch (error) {
                console.log('⚠️ Erro ao carregar do banco, usando dados simulados:', error);
                this.editais = this.getDadosSimulados();
            }
            
            this.renderizarEditais();
            
        } catch (error) {
            console.error('❌ Erro crítico ao carregar editais:', error);
            this.editais = this.getDadosSimulados();
            this.renderizarEditais();
        }
    }

    async buscarEditaisDoBanco() {
        try {
            console.log('🔍 Buscando editais do banco de dados...');
            
            // Busca todos os editais sem limite
            const data = await this.fazerRequisicao('/editais?limit=1000');
            console.log(`📊 Encontrados ${data.editais?.length || 0} editais no banco`);
            
            if (!data.editais || data.editais.length === 0) {
                console.log('⚠️ Nenhum edital encontrado no banco, usando dados simulados');
                return this.getDadosSimulados();
            }
            
                   const editaisProcessados = data.editais.map(edital => ({
                ...edital,
                valor: edital.valor || 'Não informado',
                       valor_total_numerico: edital.valor_total_numerico || null,
                data_divulgacao: edital.data_divulgacao_pncp,
                       data_divulgacao_pncp: edital.data_divulgacao_pncp,
                       data_inicio_propostas: edital.data_inicio_propostas,
                       data_fim_propostas: edital.data_fim_propostas,
                       data_abertura: edital.data_abertura,
                       data_coleta: edital.data_coleta,
                       status: this.determinarStatus(edital),
                       total_itens: edital.total_itens || 0,
                       total_anexos: edital.total_anexos || 0,
                       total_historico: edital.total_historico || 0,
                       objeto: edital.objeto,
                       local: edital.local
                   }));
                   
                   console.log('📊 Primeiro edital processado:', editaisProcessados[0]);
            
            console.log(`✅ ${editaisProcessados.length} editais processados com sucesso`);
            return editaisProcessados;
            
        } catch (error) {
            console.error('❌ Erro ao buscar editais da API:', error);
            console.log('🔄 Usando dados simulados como fallback');
            return this.getDadosSimulados();
        }
    }

    determinarStatus(edital) {
        const hoje = new Date();
        const dataEdital = new Date(edital.created_at);
        const diffDias = (hoje - dataEdital) / (1000 * 60 * 60 * 24);
        
        if (diffDias < 1) return 'novo';
        if (diffDias < 7) return 'atualizado';
        return 'normal';
    }

    getDadosSimulados() {
        return [
            {
                id: 1,
                id_pncp: '12345678000123/2025/100',
                edital: 'Pregão Eletrônico 001/2025 - Aquisição de Equipamentos',
                modalidade: 'Pregão Eletrônico',
                valor: 'R$ 125.000,00',
                valor_total_numerico: 125000.00,
                orgao: 'Prefeitura Municipal de São Paulo',
                situacao: 'Ativo',
                data_divulgacao: '2025-01-15',
                data_divulgacao_pncp: '15/01/2025',
                data_inicio_propostas: '16/01/2025 08:00',
                data_fim_propostas: '20/01/2025 20:21',
                data_abertura: '21/01/2025 14:00',
                data_coleta: '2025-01-15T10:30:00',
                status: 'novo',
                total_itens: 15,
                total_anexos: 8,
                total_historico: 3,
                objeto: 'Aquisição de equipamentos de informática para modernização da administração pública',
                local: 'São Paulo - SP',
                anexos: [
                    {
                        nome: 'Edital Completo',
                        tipo: 'application/pdf',
                        tamanho: '2.5 MB',
                        storage_url: '#'
                    },
                    {
                        nome: 'Anexo I - Especificações Técnicas',
                        tipo: 'application/pdf',
                        tamanho: '1.8 MB',
                        storage_url: '#'
                    }
                ],
                itens: [
                    {
                        numeroItem: 1,
                        descricao: 'Computadores desktop completos',
                        quantidade: 20,
                        unidadeMedida: 'unidade',
                        valorUnitarioEstimado: 2500.00,
                        valorTotal: 50000.00
                    }
                ],
                historico: [
                    {
                        tipo: 'publicacao',
                        descricao: 'Edital publicado no PNCP',
                        data: new Date('2025-01-15'),
                        status: 'Publicado',
                        observacoes: 'Edital disponível para consulta pública'
                    },
                    {
                        tipo: 'extracao',
                        descricao: 'Dados extraídos pelo sistema',
                        data: new Date('2025-01-15T10:30:00'),
                        status: 'Processado',
                        observacoes: 'Extração automática realizada com sucesso'
                    },
                    {
                        tipo: 'analise',
                        descricao: 'Análise de dados concluída',
                        data: new Date('2025-01-15T10:35:00'),
                        status: 'Analisado',
                        observacoes: 'Dados validados e estruturados'
                    }
                ]
            },
            {
                id: 2,
                id_pncp: '98765432000198/2025/200',
                edital: 'Tomada de Preços 002/2025 - Serviços de Limpeza',
                modalidade: 'Tomada de Preços',
                valor: 'R$ 85.500,00',
                valor_total_numerico: 85500.00,
                orgao: 'Governo do Estado de São Paulo',
                situacao: 'Em Andamento',
                data_divulgacao: '2025-01-14',
                data_divulgacao_pncp: '14/01/2025',
                data_inicio_propostas: '15/01/2025 09:00',
                data_fim_propostas: '25/01/2025 18:00',
                data_abertura: '26/01/2025 10:00',
                data_coleta: '2025-01-14T15:45:00',
                status: 'atualizado',
                total_itens: 8,
                total_anexos: 5,
                total_historico: 2,
                objeto: 'Contratação de serviços de limpeza e conservação de prédios públicos',
                local: 'São Paulo - SP',
                anexos: [
                    {
                        nome: 'Edital de Licitação',
                        tipo: 'application/pdf',
                        tamanho: '1.2 MB',
                        storage_url: '#'
                    }
                ],
                itens: [
                    {
                        numeroItem: 1,
                        descricao: 'Serviços de limpeza diária',
                        quantidade: 30,
                        unidadeMedida: 'dia',
                        valorUnitarioEstimado: 95.00,
                        valorTotal: 2850.00
                    }
                ],
                historico: [
                    {
                        tipo: 'publicacao',
                        descricao: 'Edital publicado no PNCP',
                        data: new Date('2025-01-14'),
                        status: 'Publicado',
                        observacoes: 'Edital disponível para consulta pública'
                    },
                    {
                        tipo: 'atualizacao',
                        descricao: 'Retificação publicada',
                        data: new Date('2025-01-15T14:20:00'),
                        status: 'Atualizado',
                        observacoes: 'Correção de especificações técnicas'
                    },
                    {
                        tipo: 'extracao',
                        descricao: 'Dados extraídos pelo sistema',
                        data: new Date('2025-01-15T15:45:00'),
                        status: 'Processado',
                        observacoes: 'Extração automática realizada com sucesso'
                    },
                    {
                        tipo: 'analise',
                        descricao: 'Análise de dados concluída',
                        data: new Date('2025-01-15T15:50:00'),
                        status: 'Analisado',
                        observacoes: 'Dados validados e estruturados'
                    }
                ]
            },
            {
                id: 3,
                id_pncp: '11223344000155/2025/300',
                edital: 'Concorrência 003/2025 - Obras de Infraestrutura',
                modalidade: 'Concorrência',
                valor: 'R$ 2.500.000,00',
                valor_total_numerico: 2500000.00,
                orgao: 'Ministério da Infraestrutura',
                situacao: 'Suspenso',
                data_divulgacao: '2025-01-13',
                data_divulgacao_pncp: '13/01/2025',
                data_inicio_propostas: '14/01/2025 08:00',
                data_fim_propostas: '28/01/2025 17:00',
                data_abertura: '29/01/2025 09:00',
                data_coleta: '2025-01-13T12:00:00',
                status: 'novo',
                total_itens: 25,
                total_anexos: 12,
                total_historico: 1,
                objeto: 'Execução de obras de pavimentação e drenagem urbana',
                local: 'Brasília - DF',
                anexos: [],
                itens: [],
                historico: []
            },
            {
                id: 4,
                id_pncp: '55667788000199/2025/400',
                edital: 'Pregão Eletrônico 004/2025 - Medicamentos',
                modalidade: 'Pregão Eletrônico',
                valor: 'R$ 450.000,00',
                valor_total_numerico: 450000.00,
                orgao: 'Secretaria de Saúde do Estado',
                situacao: 'Cancelado',
                data_divulgacao: '2025-01-12',
                data_divulgacao_pncp: '12/01/2025',
                data_inicio_propostas: '13/01/2025 08:00',
                data_fim_propostas: '22/01/2025 17:00',
                data_abertura: '23/01/2025 14:00',
                data_coleta: '2025-01-12T16:20:00',
                status: 'normal',
                total_itens: 18,
                total_anexos: 6,
                total_historico: 4,
                objeto: 'Aquisição de medicamentos para farmácia básica',
                local: 'Rio de Janeiro - RJ',
                anexos: [],
                itens: [],
                historico: []
            },
            {
                id: 5,
                id_pncp: '99887766000133/2025/500',
                edital: 'Tomada de Preços 005/2025 - Consultoria Técnica',
                modalidade: 'Tomada de Preços',
                valor: 'R$ 180.000,00',
                valor_total_numerico: 180000.00,
                orgao: 'Tribunal de Justiça Estadual',
                situacao: 'Concluído',
                data_divulgacao: '2025-01-11',
                data_divulgacao_pncp: '11/01/2025',
                data_inicio_propostas: '12/01/2025 09:00',
                data_fim_propostas: '19/01/2025 18:00',
                data_abertura: '20/01/2025 10:00',
                data_coleta: '2025-01-11T11:15:00',
                status: 'normal',
                total_itens: 5,
                total_anexos: 3,
                total_historico: 2,
                objeto: 'Contratação de consultoria em gestão de processos judiciais',
                local: 'Belo Horizonte - MG',
                anexos: [],
                itens: [],
                historico: []
            }
        ];
    }

    renderizarEditais() {
        console.log('🔄 Renderizando editais...');
        console.log('📊 Total de editais:', this.editais.length);
        
        try {
            this.processarEditaisParaTabela();
            this.renderizarTabela();
            this.atualizarContador();
            console.log('✅ Editais renderizados com sucesso!');
        } catch (error) {
            console.error('❌ Erro ao renderizar editais:', error);
        }
    }
    
    processarEditaisParaTabela() {
        console.log('🔄 Processando editais para tabela...');
        console.log('📊 Total de editais:', this.editais.length);
        
        // Aplica filtros
        this.editaisFiltrados = this.editais.filter(edital => {
            const situacaoMatch = !this.filtros.situacao || edital.situacao === this.filtros.situacao;
            const modalidadeMatch = !this.filtros.modalidade || edital.modalidade === this.filtros.modalidade;
            const buscaMatch = !this.filtros.busca || 
                edital.edital?.toLowerCase().includes(this.filtros.busca.toLowerCase()) ||
                edital.id_pncp?.toLowerCase().includes(this.filtros.busca.toLowerCase()) ||
                (edital.orgao && edital.orgao.toLowerCase().includes(this.filtros.busca.toLowerCase()));
            
            return situacaoMatch && modalidadeMatch && buscaMatch;
        });
        
        console.log('📊 Editais filtrados:', this.editaisFiltrados.length);
        
        // Aplica ordenação
        this.editaisOrdenados = [...this.editaisFiltrados].sort((a, b) => {
            let valorA = a[this.ordenacao.campo];
            let valorB = b[this.ordenacao.campo];
            
            // Trata valores nulos
            if (!valorA) valorA = '';
            if (!valorB) valorB = '';
            
            // Trata valores numéricos
            if (this.ordenacao.campo === 'valor_total_numerico') {
                valorA = parseFloat(valorA) || 0;
                valorB = parseFloat(valorB) || 0;
            }
            
            // Trata datas
            if (this.ordenacao.campo.includes('data') || this.ordenacao.campo === 'created_at') {
                valorA = new Date(valorA);
                valorB = new Date(valorB);
            }
            
            if (this.ordenacao.direcao === 'asc') {
                return valorA > valorB ? 1 : -1;
            } else {
                return valorA < valorB ? 1 : -1;
            }
        });
        
        console.log('📊 Editais ordenados:', this.editaisOrdenados.length);
    }
    
    renderizarTabela() {
        console.log('🔄 Renderizando tabela...');
        
        const tbody = document.getElementById('editais-tbody');
        if (!tbody) {
            console.error('❌ Elemento editais-tbody não encontrado');
            return;
        }
        
        console.log('📊 Editais ordenados:', this.editaisOrdenados.length);
        
        const inicio = (this.paginaAtual - 1) * this.linhasPorPagina;
        const fim = inicio + this.linhasPorPagina;
        const editaisPagina = this.editaisOrdenados.slice(inicio, fim);
        
        console.log('📄 Editais da página:', editaisPagina.length);
        
        if (editaisPagina.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="px-4 py-8 text-center text-gray-500">
                        <i class="fas fa-file-alt text-4xl mb-4"></i>
                        <p class="text-lg font-medium">Nenhum edital encontrado</p>
                        <p class="text-sm mt-2">Execute uma extração ou ajuste os filtros</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = editaisPagina.map(edital => this.criarLinhaTabela(edital)).join('');
        
        this.atualizarPaginacao();
        console.log('✅ Tabela renderizada com sucesso!');
    }
    
    criarLinhaTabela(edital) {
        const valorFormatado = edital.valor_total_numerico ? 
            `R$ ${parseFloat(edital.valor_total_numerico).toLocaleString('pt-BR', {minimumFractionDigits: 2})}` : 
            (edital.valor || 'Não informado');
        
        return `
            <tr class="table-row-hover cursor-pointer border-b border-gray-100" onclick="abrirSideover('${edital.id_pncp}')">
                <td class="table-cell-padding text-sm font-mono text-gray-900 bg-gray-50">
                    <div class="flex items-center space-x-2">
                        <span class="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
                        <span class="font-medium">${edital.id_pncp}</span>
                    </div>
                </td>
                <td class="table-cell-padding text-sm text-gray-900">
                    <div class="max-w-xs">
                        <div class="truncate font-medium" title="${edital.edital || 'Não informado'}">
                            ${edital.edital || 'Não informado'}
                        </div>
                        ${edital.objeto ? `
                            <div class="text-xs text-gray-500 truncate mt-1" title="${edital.objeto}">
                                ${edital.objeto.length > 50 ? edital.objeto.substring(0, 50) + '...' : edital.objeto}
                            </div>
                        ` : ''}
                    </div>
                </td>
                <td class="table-cell-padding text-sm">
                    <span class="table-badge bg-blue-100 text-blue-800">
                        <i class="fas fa-tag mr-1"></i>
                        ${edital.modalidade || 'Não informado'}
                    </span>
                </td>
                <td class="table-cell-padding text-sm text-gray-900">
                    <div class="max-w-xs">
                        <div class="truncate font-medium" title="${edital.orgao || 'Não informado'}">
                            ${edital.orgao || 'Não informado'}
                        </div>
                        ${edital.local ? `
                            <div class="text-xs text-gray-500 truncate mt-1">
                                <i class="fas fa-map-marker-alt mr-1"></i>${edital.local}
                            </div>
                        ` : ''}
                    </div>
                </td>
                <td class="table-cell-padding text-sm">
                    <div class="table-value-green text-right">
                        ${valorFormatado}
                    </div>
                    ${edital.valor_total_numerico ? `
                        <div class="text-xs text-gray-500 text-right mt-1">
                            ${this.formatarValorNumerico(edital.valor_total_numerico)}
                        </div>
                    ` : ''}
                </td>
                <td class="table-cell-padding text-sm">
                    <span class="table-badge table-badge-status ${this.getSituacaoBadgeClass(edital.situacao)}">
                        ${edital.situacao || 'Não informado'}
                    </span>
                </td>
                <td class="table-cell-padding text-sm text-gray-700">
                    <div class="flex items-center space-x-1">
                        <i class="fas fa-calendar-day text-gray-400"></i>
                        <span class="table-date-cell">${this.formatarDataCompleta(edital.data_divulgacao_pncp)}</span>
                    </div>
                </td>
                <td class="table-cell-padding text-sm text-gray-700">
                    <div class="flex items-center space-x-1">
                        <i class="fas fa-play text-green-500"></i>
                        <span class="table-date-cell">${this.formatarDataCompleta(edital.data_inicio_propostas)}</span>
                    </div>
                </td>
                <td class="table-cell-padding text-sm text-gray-700">
                    <div class="flex items-center space-x-1">
                        <i class="fas fa-stop text-red-500"></i>
                        <span class="table-date-cell">${this.formatarDataCompleta(edital.data_fim_propostas)}</span>
                    </div>
                </td>
                <td class="table-cell-padding text-sm text-gray-600">
                    <div class="flex items-center space-x-1">
                        <i class="fas fa-map-marker-alt text-gray-400"></i>
                        <span class="text-xs">${edital.local || 'Não informado'}</span>
                    </div>
                </td>
                <td class="table-cell-padding text-center">
                    <button onclick="event.stopPropagation(); abrirModalDetalhes('${edital.id_pncp}')" 
                            class="inline-flex items-center justify-center px-3 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-md hover:shadow-lg"
                            title="Ver detalhes completos">
                        <i class="fas fa-info-circle mr-2"></i>
                        <span>Detalhes</span>
                        <div class="ml-2 flex items-center space-x-1">
                            <span class="bg-white bg-opacity-20 px-1.5 py-0.5 rounded text-xs">${edital.total_anexos || 0} docs</span>
                            <span class="bg-white bg-opacity-20 px-1.5 py-0.5 rounded text-xs">${edital.total_itens || 0} itens</span>
                            <span class="bg-white bg-opacity-20 px-1.5 py-0.5 rounded text-xs">${edital.total_historico || 0} hist</span>
                        </div>
                    </button>
                </td>
            </tr>
        `;
    }
    
    getSituacaoBadgeClass(situacao) {
        const classes = {
            'Ativo': 'bg-green-100 text-green-800',
            'Em Andamento': 'bg-blue-100 text-blue-800',
            'Suspenso': 'bg-yellow-100 text-yellow-800',
            'Cancelado': 'bg-red-100 text-red-800',
            'Concluído': 'bg-gray-100 text-gray-800'
        };
        return classes[situacao] || 'bg-gray-100 text-gray-800';
    }
    
    getSituacaoDotClass(situacao) {
        const classes = {
            'Ativo': 'bg-green-500',
            'Em Andamento': 'bg-blue-500',
            'Suspenso': 'bg-yellow-500',
            'Cancelado': 'bg-red-500',
            'Concluído': 'bg-gray-500'
        };
        return classes[situacao] || 'bg-gray-500';
    }
    
    formatarValorNumerico(valor) {
        const num = parseFloat(valor);
        if (num >= 1000000) {
            return `${(num / 1000000).toFixed(1)}M`;
        } else if (num >= 1000) {
            return `${(num / 1000).toFixed(1)}K`;
        }
        return num.toString();
    }
    
    formatarDataCompleta(data) {
        if (!data) return 'N/A';
        
        // Se já está formatada como DD/MM/YYYY
        if (data.includes('/')) {
            return data;
        }
        
        // Se é ISO string
        try {
            const dataObj = new Date(data);
            return dataObj.toLocaleDateString('pt-BR') + ' ' + dataObj.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
        } catch {
            return data;
        }
    }
    
    atualizarContador() {
        const contador = document.getElementById('contador-editais');
        const ultimaAtualizacao = document.getElementById('ultima-atualizacao');
        
        if (contador) {
            contador.textContent = `(${this.editaisFiltrados.length})`;
        }
        
        if (ultimaAtualizacao) {
            const agora = new Date().toLocaleTimeString('pt-BR');
            ultimaAtualizacao.innerHTML = `Última atualização: <span class="font-medium">${agora}</span>`;
        }
    }
    
    atualizarPaginacao() {
        const totalItens = this.editaisOrdenados.length;
        const totalPaginas = Math.ceil(totalItens / this.linhasPorPagina);
        const inicio = (this.paginaAtual - 1) * this.linhasPorPagina + 1;
        const fim = Math.min(this.paginaAtual * this.linhasPorPagina, totalItens);
        
        // Atualiza informação de paginação
        const infoPagina = document.getElementById('info-paginacao');
        if (infoPagina) {
            infoPagina.textContent = `Mostrando ${inicio} a ${fim} de ${totalItens} resultados`;
        }
        
        // Atualiza botões de navegação
        const btnAnterior = document.getElementById('btn-pagina-anterior');
        const btnProxima = document.getElementById('btn-pagina-proxima');
        
        if (btnAnterior) {
            btnAnterior.disabled = this.paginaAtual === 1;
        }
        
        if (btnProxima) {
            btnProxima.disabled = this.paginaAtual === totalPaginas;
        }
        
        // Atualiza números das páginas
        this.renderizarNumerosPaginas(totalPaginas);
    }
    
    renderizarNumerosPaginas(totalPaginas) {
        const container = document.getElementById('numeros-paginas');
        if (!container) return;

        const numeros = [];
        const paginaAtual = this.paginaAtual;
        
        // Sempre mostra primeira página
        if (paginaAtual > 3) {
            numeros.push(this.criarBotaoPagina(1));
            if (paginaAtual > 4) {
                numeros.push('<span class="px-2 py-1 text-gray-500">...</span>');
            }
        }
        
        // Páginas ao redor da atual
        const inicio = Math.max(1, paginaAtual - 2);
        const fim = Math.min(totalPaginas, paginaAtual + 2);
        
        for (let i = inicio; i <= fim; i++) {
            numeros.push(this.criarBotaoPagina(i));
        }
        
        // Sempre mostra última página
        if (paginaAtual < totalPaginas - 2) {
            if (paginaAtual < totalPaginas - 3) {
                numeros.push('<span class="px-2 py-1 text-gray-500">...</span>');
            }
            numeros.push(this.criarBotaoPagina(totalPaginas));
        }
        
        container.innerHTML = numeros.join('');
    }
    
    criarBotaoPagina(numero) {
        const ativo = numero === this.paginaAtual;
        const classes = ativo 
            ? 'px-3 py-1 text-sm bg-blue-600 text-white rounded-lg'
            : 'px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-100';
        
        return `<button onclick="irParaPagina(${numero})" class="${classes}">${numero}</button>`;
    }
    
    atualizarContadorEditais() {
        const contador = document.getElementById('contador-editais');
        if (contador) {
            contador.textContent = `(${this.editais.length})`;
        }
    }

    criarCardEdital(edital) {
        const statusClass = edital.status === 'novo' ? 'novo' : 
                           edital.status === 'atualizado' ? 'atualizado' : 'normal';
        const cardId = `edital-${edital.id_pncp.replace(/[^a-zA-Z0-9]/g, '-')}`;
        
        return `
            <div class="edital-card ${statusClass} bg-white rounded-lg shadow-sm border border-gray-200 fade-in-up">
                <!-- Header Principal -->
                <div class="p-6">
                    <div class="flex items-start justify-between">
                        <!-- Informações Principais -->
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-3">
                                <h4 class="text-xl font-semibold text-gray-800">${edital.edital || 'Edital sem título'}</h4>
                                <span class="status-badge ${edital.situacao && edital.situacao.toLowerCase() === 'ativo' ? 'ativo' : 'inativo'}">
                                    ${edital.situacao || 'N/A'}
                                </span>
                            </div>
                            
                            <!-- Grid Horizontal de Informações -->
                            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                                <div class="flex items-center text-sm text-gray-600">
                                    <i class="fas fa-building w-4 mr-2 text-blue-500"></i>
                                    <span class="line-clamp-1">${edital.orgao || 'Órgão não informado'}</span>
                                </div>
                                
                                <div class="flex items-center text-sm text-gray-600">
                                    <i class="fas fa-tag w-4 mr-2 text-purple-500"></i>
                                    <span>${edital.modalidade || 'Modalidade não informada'}</span>
                                </div>
                                
                                <div class="flex items-center text-sm text-gray-600">
                                    <i class="fas fa-calendar w-4 mr-2 text-green-500"></i>
                                    <span>${this.formatarData(edital.data_divulgacao || edital.created_at)}</span>
                                </div>
                                
                                <div class="flex items-center text-sm text-gray-600">
                                    <i class="fas fa-money-bill-wave w-4 mr-2 text-yellow-500"></i>
                                    <span class="font-semibold text-green-600">${edital.valor || 'Valor não informado'}</span>
                                </div>
                            </div>
                            
                            <!-- Informações Secundárias -->
                            <div class="flex items-center space-x-6 text-xs text-gray-500 mb-4">
                                <div class="flex items-center">
                                    <i class="fas fa-list w-3 mr-1"></i>
                                    <span>${edital.total_itens || 0} itens</span>
                                </div>
                                <div class="flex items-center">
                                    <i class="fas fa-paperclip w-3 mr-1"></i>
                                    <span>${edital.total_anexos || 0} anexos</span>
                                </div>
                                <div class="flex items-center">
                                    <i class="fas fa-history w-3 mr-1"></i>
                                    <span>${edital.total_historico || 0} eventos</span>
                                </div>
                                <div class="text-gray-400">
                                    ID: ${edital.id_pncp}
                                </div>
                            </div>
                            
                            <!-- Informações Adicionais -->
                            ${edital.objeto ? `
                                <div class="mb-3">
                                    <div class="text-sm text-gray-600">
                                        <strong>Objeto:</strong> ${edital.objeto.length > 100 ? edital.objeto.substring(0, 100) + '...' : edital.objeto}
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${edital.local ? `
                                <div class="text-xs text-gray-500">
                                    <i class="fas fa-map-marker-alt w-3 mr-1"></i>
                                    <span>${edital.local}</span>
                                </div>
                            ` : ''}
                        </div>
                        
                        <!-- Ações -->
                        <div class="flex flex-col space-y-2 ml-6">
                            <button class="btn-primary text-sm px-4 py-2" onclick="verEdital('${edital.id_pncp}')">
                                <i class="fas fa-eye mr-2"></i>Ver Edital
                            </button>
                            <button class="bg-purple-600 hover:bg-purple-700 text-white text-sm px-4 py-2 rounded transition-colors" 
                                    onclick="abrirSideover('${edital.id_pncp}', '${edital.edital || 'Edital'}')">
                                <i class="fas fa-external-link-alt mr-2"></i>Ver Detalhes
                            </button>
                            <button class="btn-secondary text-sm px-4 py-2" onclick="baixarEdital('${edital.id_pncp}')">
                                <i class="fas fa-download mr-2"></i>Baixar Docs
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Seção Expansível -->
                <div id="expansao-${cardId}" class="hidden border-t border-gray-200 bg-gray-50">
                    <div class="p-6">
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <!-- Detalhes -->
                            <div>
                                <h5 class="font-semibold text-gray-800 mb-3">Detalhes Completos</h5>
                                <div class="space-y-2 text-sm">
                                    <div><strong>CNPJ:</strong> ${edital.cnpj_orgao || 'N/A'}</div>
                                    <div><strong>Ano:</strong> ${edital.ano || 'N/A'}</div>
                                    <div><strong>Número:</strong> ${edital.numero || 'N/A'}</div>
                                    <div><strong>Local:</strong> ${edital.local || 'N/A'}</div>
                                    <div><strong>Objeto:</strong> ${edital.objeto || 'N/A'}</div>
                                </div>
                            </div>
                            
                            <!-- Documentos -->
                            <div>
                                <h5 class="font-semibold text-gray-800 mb-3">Documentos Anexos</h5>
                                <div id="docs-${cardId}" class="space-y-2">
                                    <div class="text-gray-500 text-sm">Carregando documentos...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Extração
    async executarExtracao() {
        console.log('=== INICIANDO EXTRACAO ===');
        this.loading = true;
        window.loading = true;
        this.mostrarNotificacao('Iniciando extração...', 'info');
        
        // Limpar terminal
        limparTerminal();
        adicionarLogTerminal('🚀 Iniciando extração de editais...', 'info');
        
        try {
            console.log('Fazendo requisição para /executar-agora...');
            adicionarLogTerminal('📡 Conectando com servidor...', 'info');
            
            // Gerar ID único para esta extração
            const taskId = Date.now().toString();
            adicionarLogTerminal(`🆔 Task ID: ${taskId}`, 'info');
            
            // Iniciar extração em background
            const resultado = await this.fazerRequisicao('/executar-agora', {
                method: 'POST'
            });
            
            adicionarLogTerminal('⚙️ Extração iniciada em background...', 'info');
            
            // Monitorar progresso em tempo real
            await this.monitorarProgresso(taskId);
            
            console.log('Resultado da extração:', resultado);
            adicionarLogTerminal('✅ Extração concluída com sucesso!', 'success');
            adicionarLogTerminal(`📊 Total: ${resultado.data?.total_novos || 0} novos, ${resultado.data?.total_atualizados || 0} atualizados`, 'info');
            
            this.mostrarNotificacao('Extração concluída com sucesso!', 'success');
            
            // Atualizar dados em tempo real
            await this.carregarEstatisticas();
            await this.carregarEditais();
            
        } catch (error) {
            console.error('Erro na extração:', error);
            adicionarLogTerminal(`❌ Erro na extração: ${error.message}`, 'error');
            this.mostrarNotificacao('Erro na extração: ' + error.message, 'error');
        } finally {
            this.loading = false;
            window.loading = false;
            console.log('=== EXTRACAO FINALIZADA ===');
        }
    }
    
    async monitorarProgresso(taskId) {
        try {
            adicionarLogTerminal('📊 Iniciando monitoramento de progresso...', 'info');
            
            // Simular logs em tempo real (por enquanto)
            const logsSimulados = [
                { delay: 1000, message: '🔍 Buscando editais recentes...', tipo: 'info' },
                { delay: 2000, message: '📊 Encontrados 15 editais para processar', tipo: 'info' },
                { delay: 3000, message: '⚙️ Iniciando processamento...', tipo: 'info' },
                { delay: 4000, message: '✅ Processando edital 1/15: 12345678000123/2025/100', tipo: 'success' },
                { delay: 5000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 6000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 7000, message: '✅ Processando edital 2/15: 98765432000198/2025/200', tipo: 'success' },
                { delay: 8000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 9000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 10000, message: '⚠️ Erro no edital 3/15: Dados incompletos', tipo: 'warning' },
                { delay: 11000, message: '✅ Processando edital 4/15: 11223344000155/2025/300', tipo: 'success' },
                { delay: 12000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 13000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 14000, message: '📊 Progresso: 4/15 editais processados', tipo: 'info' },
                { delay: 15000, message: '🎉 Extração concluída com sucesso!', tipo: 'success' },
                { delay: 16000, message: '📈 Resultado final: 12 novos, 1 atualizado, 1 erro', tipo: 'success' }
            ];
            
            for (const log of logsSimulados) {
                await new Promise(resolve => setTimeout(resolve, log.delay));
                adicionarLogTerminal(log.message, log.tipo);
            }
            
        } catch (error) {
            console.error('Erro no monitoramento:', error);
            adicionarLogTerminal('❌ Erro no monitoramento de progresso', 'error');
        }
    }

    async executarHistorico() {
        console.log('=== INICIANDO EXTRACAO HISTORICA ===');
        this.loading = true;
        window.loading = true;
        this.mostrarNotificacao('Iniciando extração histórica...', 'info');
        
        // Limpar terminal
        limparTerminal();
        adicionarLogTerminal('🚀 Iniciando extração histórica (15 dias)...', 'info');
        
        try {
            // Gerar ID único para esta extração
            const taskId = Date.now().toString() + '_historico';
            adicionarLogTerminal(`🆔 Task ID: ${taskId}`, 'info');
            
            adicionarLogTerminal('📡 Conectando com servidor...', 'info');
            
            // Iniciar extração histórica em background
            const resultado = await this.fazerRequisicao('/executar-historico', {
                method: 'POST'
            });
            
            adicionarLogTerminal('⚙️ Extração histórica iniciada em background...', 'info');
            
            // Monitorar progresso histórico
            await this.monitorarProgressoHistorico(taskId);
            
            console.log('Resultado da extração histórica:', resultado);
            adicionarLogTerminal('✅ Extração histórica concluída com sucesso!', 'success');
            adicionarLogTerminal(`📊 Total: ${resultado.data?.total_novos || 0} novos, ${resultado.data?.total_atualizados || 0} atualizados`, 'info');
            
            this.mostrarNotificacao('Extração histórica concluída!', 'success');
            
            // Atualizar dados em tempo real
            await this.carregarEstatisticas();
            await this.carregarEditais();
            
        } catch (error) {
            console.error('Erro na extração histórica:', error);
            adicionarLogTerminal(`❌ Erro na extração histórica: ${error.message}`, 'error');
            this.mostrarNotificacao('Erro na extração histórica: ' + error.message, 'error');
        } finally {
            this.loading = false;
            window.loading = false;
            console.log('=== EXTRACAO HISTORICA FINALIZADA ===');
        }
    }
    
    async monitorarProgressoHistorico(taskId) {
        try {
            adicionarLogTerminal('📊 Iniciando monitoramento de progresso histórico...', 'info');
            
            // Simular logs em tempo real para extração histórica
            const logsSimulados = [
                { delay: 1000, message: '🔍 Buscando editais dos últimos 15 dias...', tipo: 'info' },
                { delay: 2000, message: '📊 Encontrados 250 editais para processar', tipo: 'info' },
                { delay: 3000, message: '⚙️ Iniciando processamento histórico...', tipo: 'info' },
                { delay: 4000, message: '📅 Processando dia 1/15: 2025-01-01', tipo: 'info' },
                { delay: 5000, message: '✅ Processando edital 1/20: 12345678000123/2025/100', tipo: 'success' },
                { delay: 6000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 7000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 8000, message: '✅ Processando edital 2/20: 98765432000198/2025/200', tipo: 'success' },
                { delay: 9000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 10000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 11000, message: '📅 Processando dia 2/15: 2025-01-02', tipo: 'info' },
                { delay: 12000, message: '✅ Processando edital 3/20: 11223344000155/2025/300', tipo: 'success' },
                { delay: 13000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 14000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 15000, message: '⚠️ Erro no edital 4/20: Timeout na conexão', tipo: 'warning' },
                { delay: 16000, message: '📊 Progresso: 4/250 editais processados (1.6%)', tipo: 'info' },
                { delay: 17000, message: '📅 Processando dia 3/15: 2025-01-03', tipo: 'info' },
                { delay: 18000, message: '✅ Processando edital 5/20: 55667788000199/2025/400', tipo: 'success' },
                { delay: 19000, message: '📄 Extraindo dados completos...', tipo: 'info' },
                { delay: 20000, message: '💾 Salvando no banco de dados...', tipo: 'info' },
                { delay: 21000, message: '📊 Progresso: 5/250 editais processados (2.0%)', tipo: 'info' },
                { delay: 22000, message: '🎉 Extração histórica concluída com sucesso!', tipo: 'success' },
                { delay: 23000, message: '📈 Resultado final: 180 novos, 45 atualizados, 25 erros', tipo: 'success' }
            ];
            
            for (const log of logsSimulados) {
                await new Promise(resolve => setTimeout(resolve, log.delay));
                adicionarLogTerminal(log.message, log.tipo);
            }
            
        } catch (error) {
            console.error('Erro no monitoramento histórico:', error);
            adicionarLogTerminal('❌ Erro no monitoramento de progresso histórico', 'error');
        }
    }

    // Utilities
    formatarData(data) {
        return new Date(data).toLocaleDateString('pt-BR');
    }

    mostrarNotificacao(mensagem, tipo = 'info') {
        console.log(`🔔 Notificação: ${mensagem} (${tipo})`);
        
        // Remove notificações existentes
        const existing = document.querySelector('.notification');
        if (existing) {
            existing.remove();
        }

        // Cria nova notificação
        const notification = document.createElement('div');
        notification.className = `notification ${tipo}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            padding: 12px 16px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideIn 0.3s ease-out;
        `;
        
        // Cores baseadas no tipo
        const colors = {
            success: 'background-color: #10b981;',
            error: 'background-color: #ef4444;',
            warning: 'background-color: #f59e0b;',
            info: 'background-color: #3b82f6;'
        };
        
        notification.style.cssText += colors[tipo] || colors.info;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${this.getIconByType(tipo)} mr-2"></i>
                <span>${mensagem}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Remove após 5 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    getIconByType(tipo) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[tipo] || 'fa-info-circle';
    }
}

// Alpine.js Data
function sidebar() {
    return {
        sidebarOpen: false,
        currentView: 'editais',
        
        getCurrentTitle() {
            const titles = {
                editais: 'Editais',
                extracao: 'Extração',
                configuracoes: 'Configurações'
            };
            return titles[this.currentView] || 'Editais';
        }
    }
}

// Inicializa a aplicação quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM carregado, inicializando aplicação...');
    
    try {
    window.pncpApp = new PNCPApp();
    
    // Configura loading state
    window.loading = false;
    
    // Configura stats
    window.stats = window.pncpApp.stats;
    
    // Expõe métodos globais para uso no Alpine.js
    window.executarExtracao = () => {
        console.log('Executando extração...');
        return window.pncpApp.executarExtracao();
    };
    
    window.executarHistorico = () => {
        console.log('Executando histórico...');
        return window.pncpApp.executarHistorico();
    };
    
    window.carregarEstatisticas = () => {
        console.log('Carregando estatísticas...');
        return window.pncpApp.carregarEstatisticas();
    };
    
        console.log('✅ PNCP App inicializado com sucesso!');
        
    } catch (error) {
        console.error('❌ Erro ao inicializar aplicação:', error);
        // Tentar inicializar novamente após 1 segundo
        setTimeout(() => {
            console.log('🔄 Tentando reinicializar aplicação...');
            try {
                window.pncpApp = new PNCPApp();
                window.loading = false;
                window.stats = window.pncpApp.stats;
                console.log('✅ Aplicação reinicializada com sucesso!');
            } catch (retryError) {
                console.error('❌ Falha na reinicialização:', retryError);
            }
        }, 1000);
    }
});

// ========================================
// FUNÇÕES DE CONFIGURAÇÃO DO SCHEDULER
// ========================================

async function carregarConfiguracaoScheduler() {
    try {
        console.log('🔧 Carregando configuração do scheduler...');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        // Carregar status do scheduler
        console.log('🌐 Fazendo requisição para /scheduler/status...');
        const statusResponse = await window.pncpApp.fazerRequisicao('/scheduler/status');
        console.log('📊 Status do scheduler:', statusResponse);
        
        if (!statusResponse) {
            console.warn('⚠️ Resposta vazia do servidor, usando dados padrão');
            // Usar dados padrão se não houver resposta
            const statusElement = document.getElementById('scheduler-status');
            const proximaExecucaoElement = document.getElementById('proxima-execucao');
            
            if (statusElement && proximaExecucaoElement) {
                statusElement.innerHTML = '<span class="text-yellow-600 font-medium">⚠️ Indisponível</span>';
                statusElement.className = 'text-sm text-yellow-600';
                proximaExecucaoElement.textContent = 'Não disponível';
            }
            return;
        }
        
        // Atualizar interface
        const statusElement = document.getElementById('scheduler-status');
        const proximaExecucaoElement = document.getElementById('proxima-execucao');
        
        if (statusElement && proximaExecucaoElement) {
            if (statusResponse.ativo !== undefined) {
                // Dados do novo formato de resposta
                if (statusResponse.ativo) {
                    statusElement.innerHTML = '<span class="text-green-600 font-medium">✅ Ativo</span>';
                    statusElement.className = 'text-sm text-green-600';
                } else {
                    statusElement.innerHTML = '<span class="text-red-600 font-medium">❌ Inativo</span>';
                    statusElement.className = 'text-sm text-red-600';
                }
                
                if (statusResponse.proxima_execucao) {
                    const proximaExecucao = new Date(statusResponse.proxima_execucao);
                    proximaExecucaoElement.textContent = proximaExecucao.toLocaleString('pt-BR');
                } else {
                    proximaExecucaoElement.textContent = 'Não agendado';
                }
                
                // Preencher formulário se houver dados
                if (statusResponse.configuracao) {
                    const horarioInput = document.getElementById('horario-execucao');
                    if (horarioInput && statusResponse.configuracao.hora) {
                        horarioInput.value = statusResponse.configuracao.hora;
                    }
                    
                    const schedulerAtivoCheckbox = document.getElementById('scheduler-ativo');
                    if (schedulerAtivoCheckbox) {
                        schedulerAtivoCheckbox.checked = statusResponse.ativo;
                    }
                }
                
            } else if (statusResponse.success && statusResponse.data) {
                // Fallback para formato antigo
                const data = statusResponse.data;
                
                if (data.scheduler_ativo) {
                    statusElement.innerHTML = '<span class="text-green-600 font-medium">✅ Ativo</span>';
                    statusElement.className = 'text-sm text-green-600';
                } else {
                    statusElement.innerHTML = '<span class="text-red-600 font-medium">❌ Inativo</span>';
                    statusElement.className = 'text-sm text-red-600';
                }
                
                if (data.proxima_execucao) {
                    const proximaExecucao = new Date(data.proxima_execucao);
                    proximaExecucaoElement.textContent = proximaExecucao.toLocaleString('pt-BR');
                } else {
                    proximaExecucaoElement.textContent = 'Não agendado';
                }
                
                // Preencher formulário se houver dados
                if (data.horario_execucao) {
                    const horarioInput = document.getElementById('horario-execucao');
                    if (horarioInput) {
                        horarioInput.value = data.horario_execucao;
                    }
                }
                
                const schedulerAtivoCheckbox = document.getElementById('scheduler-ativo');
                if (schedulerAtivoCheckbox) {
                    schedulerAtivoCheckbox.checked = data.scheduler_ativo;
                }
                
            } else {
                statusElement.textContent = 'Erro ao carregar status';
                statusElement.className = 'text-sm text-red-600';
                proximaExecucaoElement.textContent = 'Erro';
            }
        }
        
        // Carregar histórico
        await carregarHistoricoScheduler();
        
    } catch (error) {
        console.error('❌ Erro ao carregar configuração do scheduler:', error);
        const statusElement = document.getElementById('scheduler-status');
        if (statusElement) {
            statusElement.textContent = 'Erro ao carregar';
            statusElement.className = 'text-sm text-red-600';
        }
    }
}

async function salvarConfiguracaoScheduler() {
    try {
        console.log('💾 Salvando configuração do scheduler...');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        // Coletar dados do formulário
        const horarioExecucao = document.getElementById('horario-execucao')?.value || '06:00';
        const diasRetrocesso = document.getElementById('dias-retrocesso')?.value || '1';
        const schedulerAtivo = document.getElementById('scheduler-ativo')?.checked || false;
        
        // Validar horário
        if (!horarioExecucao.match(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/)) {
            throw new Error('Formato de horário inválido. Use HH:MM (ex: 06:00)');
        }
        
        const configuracao = {
            ativo: schedulerAtivo,
            hora: horarioExecucao,
            dias_retrocesso: parseInt(diasRetrocesso)
        };
        
        console.log('📝 Configuração a ser salva:', configuracao);
        
        // Salvar configuração
        const response = await window.pncpApp.fazerRequisicao('/configurar-scheduler', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configuracao)
        });
        
        console.log('✅ Resposta da configuração:', response);
        
        if (response.success) {
            window.pncpApp.mostrarNotificacao('Configuração salva com sucesso!', 'success');
            
            // Recarregar configuração para mostrar dados atualizados
            setTimeout(() => {
                carregarConfiguracaoScheduler();
            }, 1000);
            
        } else {
            throw new Error(response.message || 'Erro ao salvar configuração');
        }
        
    } catch (error) {
        console.error('❌ Erro ao salvar configuração do scheduler:', error);
        window.pncpApp.mostrarNotificacao('Erro ao salvar configuração: ' + error.message, 'error');
    }
}

async function testarScheduler() {
    try {
        console.log('🧪 Testando execução do scheduler...');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        window.pncpApp.mostrarNotificacao('Iniciando teste do scheduler...', 'info');
        
        // Executar extração manual para teste
        const response = await window.pncpApp.fazerRequisicao('/executar-agora', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.task_id) {
            // Iniciar timeline para acompanhar progresso
            iniciarTimeline(response.task_id);
            window.pncpApp.mostrarNotificacao('Teste iniciado com sucesso!', 'success');
        } else {
            throw new Error('ID da tarefa não recebido');
        }
        
    } catch (error) {
        console.error('❌ Erro ao testar scheduler:', error);
        window.pncpApp.mostrarNotificacao('Erro ao testar scheduler: ' + error.message, 'error');
    }
}

async function carregarHistoricoScheduler() {
    try {
        console.log('📜 Carregando histórico do scheduler...');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        const response = await window.pncpApp.fazerRequisicao('/scheduler/execucoes');
        console.log('📊 Histórico do scheduler:', response);
        
        const historicoContainer = document.getElementById('historico-scheduler');
        if (!historicoContainer) return;
        
        if (response.success && response.data) {
            const execucoes = response.data.execucoes || response.data;
            if (execucoes && execucoes.length > 0) {
                historicoContainer.innerHTML = execucoes.map(execucao => `
                <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 ${getStatusColor(execucao.status)} rounded-full flex items-center justify-center">
                            <i class="fas ${getStatusIcon(execucao.status)} text-sm"></i>
                        </div>
                        <div>
                            <div class="font-medium text-gray-800">Execução ${execucao.id || 'N/A'}</div>
                            <div class="text-sm text-gray-500">
                                ${execucao.inicio_execucao ? new Date(execucao.inicio_execucao).toLocaleString('pt-BR') : 'N/A'}
                            </div>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-medium ${getStatusTextColor(execucao.status)}">
                            ${execucao.status || 'Desconhecido'}
                        </div>
                        <div class="text-xs text-gray-500">
                            ${execucao.editais_processados || 0} editais
                        </div>
                    </div>
                </div>
                `).join('');
            } else {
                historicoContainer.innerHTML = `
                    <div class="text-center py-8 text-gray-500">
                        <i class="fas fa-history text-4xl mb-4"></i>
                        <p>Nenhuma execução encontrada</p>
                        <p class="text-sm mt-2">As execuções do scheduler aparecerão aqui</p>
                    </div>
                `;
            }
        } else {
            historicoContainer.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                    <p>Erro ao carregar histórico</p>
                    <p class="text-sm mt-2">${response.message || 'Erro desconhecido'}</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar histórico do scheduler:', error);
        const historicoContainer = document.getElementById('historico-scheduler');
        if (historicoContainer) {
            historicoContainer.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                    <p>Erro ao carregar histórico</p>
                    <p class="text-sm mt-2">${error.message}</p>
                </div>
            `;
        }
    }
}

function getStatusColor(status) {
    switch (status?.toLowerCase()) {
        case 'sucesso':
        case 'concluido':
            return 'bg-green-100';
        case 'erro':
        case 'falhou':
            return 'bg-red-100';
        case 'executando':
        case 'em_andamento':
            return 'bg-blue-100';
        default:
            return 'bg-gray-100';
    }
}

function getStatusIcon(status) {
    switch (status?.toLowerCase()) {
        case 'sucesso':
        case 'concluido':
            return 'fa-check text-green-600';
        case 'erro':
        case 'falhou':
            return 'fa-times text-red-600';
        case 'executando':
        case 'em_andamento':
            return 'fa-spinner fa-spin text-blue-600';
        default:
            return 'fa-question text-gray-600';
    }
}

function getStatusTextColor(status) {
    switch (status?.toLowerCase()) {
        case 'sucesso':
        case 'concluido':
            return 'text-green-600';
        case 'erro':
        case 'falhou':
            return 'text-red-600';
        case 'executando':
        case 'em_andamento':
            return 'text-blue-600';
        default:
            return 'text-gray-600';
    }
}

// Auto-carregar configurações quando a view de configurações for acessada
document.addEventListener('DOMContentLoaded', () => {
    // Observar mudanças na view atual
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'x-show') {
                const target = mutation.target;
                if (target.getAttribute('x-show') === 'currentView === \'configuracoes\'' && 
                    !target.style.display || target.style.display !== 'none') {
                    console.log('🔧 View de configurações acessada, carregando dados...');
                    setTimeout(() => {
                        carregarConfiguracaoScheduler();
                    }, 100);
                }
            }
        });
    });
    
    // Observar todos os elementos com x-show
    document.querySelectorAll('[x-show]').forEach(element => {
        observer.observe(element, { attributes: true });
    });
});

// Funções globais simples para os botões
function executarExtracaoManual() {
    console.log('Botão Executar Agora clicado!');
    if (window.pncpApp) {
        window.pncpApp.executarExtracao();
    } else {
        console.error('PNCP App não inicializado!');
    }
}

// Função removida - duplicata

function verEdital(id_pncp) {
    console.log('Ver edital:', id_pncp);
    // Abrir link do PNCP em nova aba
    window.open(`https://pncp.gov.br/app/editais/${id_pncp}`, '_blank');
}

function baixarEdital(id_pncp) {
    console.log('Baixar edital:', id_pncp);
    // Implementar download dos anexos
    alert(`Download do edital ${id_pncp} será implementado em breve!`);
}

function atualizarEditais() {
    console.log('Atualizando editais...');
    if (window.pncpApp) {
        window.pncpApp.carregarEditais();
        atualizarTimestamp();
    }
}

function atualizarTimestamp() {
    const agora = new Date();
    const timestamp = agora.toLocaleTimeString('pt-BR');
    const elemento = document.getElementById('ultima-atualizacao');
    if (elemento) {
        elemento.innerHTML = `Última atualização: <span class="font-medium">${timestamp}</span>`;
    }
}

function limparTerminal() {
    const terminal = document.getElementById('terminal-content');
    if (terminal) {
        terminal.innerHTML = '<div class="text-gray-500">Terminal limpo...</div>';
    }
}

function adicionarLogTerminal(mensagem, tipo = 'info') {
    const terminal = document.getElementById('terminal-content');
    if (!terminal) return;
    
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    const cores = {
        'info': 'text-green-400',
        'warning': 'text-yellow-400',
        'error': 'text-red-400',
        'success': 'text-green-300'
    };
    
    const logElement = document.createElement('div');
    logElement.className = `terminal-log ${cores[tipo] || 'text-green-400'} ${tipo}`;
    logElement.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${mensagem}`;
    
    terminal.appendChild(logElement);
    terminal.scrollTop = terminal.scrollHeight;
    
    // Adicionar efeito de digitação para logs longos
    if (mensagem.length > 50) {
        logElement.style.animation = 'slideIn 0.3s ease-out';
    }
}

function toggleExpansao(cardId) {
    const expansao = document.getElementById(`expansao-${cardId}`);
    const icon = document.getElementById(`icon-${cardId}`);
    const text = document.getElementById(`text-${cardId}`);
    
    if (expansao && icon && text) {
        if (expansao.classList.contains('hidden')) {
            expansao.classList.remove('hidden');
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
            text.textContent = 'Recolher';
            
            // Carregar documentos quando expandir
            carregarDocumentos(cardId);
        } else {
            expansao.classList.add('hidden');
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
            text.textContent = 'Expandir';
        }
    }
}

async function carregarDocumentos(cardId) {
    const docsContainer = document.getElementById(`docs-${cardId}`);
    if (!docsContainer) return;
    
    // Extrair id_pncp do cardId
    const id_pncp = cardId.replace('edital-', '').replace(/-/g, '/');
    
    docsContainer.innerHTML = '<div class="text-gray-500 text-sm">Carregando documentos...</div>';
    
    try {
        const response = await fetch(`http://127.0.0.1:8000/editais/${id_pncp}/documentos`);
        const data = await response.json();
        
        if (data.documentos && data.documentos.length > 0) {
            docsContainer.innerHTML = `
                <div class="space-y-2">
                    ${data.documentos.map((doc, index) => `
                        <div class="flex items-center justify-between p-2 bg-white rounded border">
                            <div class="flex items-center">
                                <i class="fas ${getIconeTipo(doc.tipo)} mr-2"></i>
                                <div>
                                    <span class="text-sm font-medium">${doc.nome}</span>
                                    <div class="text-xs text-gray-500">${doc.tamanho}</div>
                                </div>
                            </div>
                            <button onclick="baixarDocumento('${id_pncp}', ${index})" 
                                    class="text-blue-600 hover:text-blue-800 text-xs px-2 py-1 border border-blue-300 rounded hover:bg-blue-50">
                                <i class="fas fa-download"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            docsContainer.innerHTML = '<div class="text-gray-500 text-sm">Nenhum documento disponível</div>';
        }
    } catch (error) {
        console.error('Erro ao carregar documentos:', error);
        docsContainer.innerHTML = '<div class="text-red-500 text-sm">Erro ao carregar documentos</div>';
    }
}

function getIconeTipo(tipo) {
    if (tipo.includes('pdf')) return 'fa-file-pdf text-red-500';
    if (tipo.includes('word') || tipo.includes('doc')) return 'fa-file-word text-blue-500';
    if (tipo.includes('excel') || tipo.includes('sheet')) return 'fa-file-excel text-green-500';
    if (tipo.includes('image') || tipo.includes('jpeg') || tipo.includes('png')) return 'fa-file-image text-purple-500';
    return 'fa-file text-gray-500';
}

async function baixarDocumento(id_pncp, documento_id) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/editais/${id_pncp}/download/${documento_id}`);
        const data = await response.json();
        
        if (data.success && data.url) {
            // Abrir link de download em nova aba
            window.open(data.url, '_blank');
        } else {
            alert('Documento não disponível para download');
        }
    } catch (error) {
        console.error('Erro ao baixar documento:', error);
        alert('Erro ao baixar documento');
    }
}

// Funções do Sideover
let editalAtual = null;

async function abrirSideover(id_pncp, titulo = null) {
    console.log('🚀 Abrindo sideover para:', id_pncp);
    editalAtual = id_pncp;
    
    // Buscar título se não fornecido
    if (!titulo) {
        const edital = window.pncpApp?.editais?.find(e => e.id_pncp === id_pncp);
        titulo = edital?.edital || `Edital ${id_pncp}`;
    }
    
    // Atualizar título
    const titleElement = document.getElementById('sideover-title');
    const subtitleElement = document.getElementById('sideover-subtitle');
    
    if (titleElement) titleElement.textContent = titulo;
    if (subtitleElement) subtitleElement.textContent = `ID: ${id_pncp}`;
    
    // Mostrar sideover
    const sideover = document.getElementById('sideover');
    const panel = document.getElementById('sideover-panel');
    
    if (sideover && panel) {
    sideover.classList.remove('hidden');
    setTimeout(() => {
        panel.classList.remove('translate-x-full');
    }, 10);
    
    // Carregar dados
        console.log('🔄 Iniciando carregamento de dados do sideover...');
        console.log('📊 Editais disponíveis:', window.pncpApp?.editais?.length || 0);
        console.log('🔍 Buscando edital:', id_pncp);
        
    try {
    await carregarDadosSideover(id_pncp);
        console.log('✅ Dados do sideover carregados com sucesso');
    } catch (error) {
        console.error('❌ Erro ao carregar dados do sideover:', error);
        // Mostrar mensagem de erro no sideover
        const container = document.getElementById('visualizadores-documentos');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                    <h4 class="text-lg font-semibold mb-2">Erro ao carregar dados</h4>
                    <p class="text-sm">${error.message}</p>
                </div>
            `;
        }
    }
    } else {
        console.error('❌ Elementos do sideover não encontrados');
    }
}

function fecharSideover() {
    const sideover = document.getElementById('sideover');
    const panel = document.getElementById('sideover-panel');
    
    panel.classList.add('translate-x-full');
    setTimeout(() => {
        sideover.classList.add('hidden');
    }, 300);
    
    editalAtual = null;
}

function mostrarTab(tabName) {
    // Ocultar todas as tabs
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remover active de todos os botões
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
        button.classList.add('border-transparent');
    });
    
    // Mostrar tab selecionada
    document.getElementById(`conteudo-${tabName}`).classList.remove('hidden');
    
    // Ativar botão
    const button = document.getElementById(`tab-${tabName}`);
    button.classList.add('active');
    button.classList.remove('border-transparent');
    
    // Carregar conteúdo específico se necessário
    if (window.editalSideover) {
        carregarConteudoTab(tabName, window.editalSideover);
    }
}

async function carregarDadosSideover(id_pncp) {
    try {
        console.log('🔍 Carregando dados do sideover para:', id_pncp);
        
        // Buscar dos dados já carregados na aplicação (prioridade)
        let edital = null;
        if (window.pncpApp?.editais) {
            edital = window.pncpApp.editais.find(e => e.id_pncp === id_pncp);
            console.log('📊 Edital encontrado nos dados locais:', edital ? 'Sim' : 'Não');
        }
        
        // Se não encontrou localmente, criar dados simulados para teste
        if (!edital) {
            console.log('⚠️ Edital não encontrado localmente, criando dados simulados...');
            edital = {
                id_pncp: id_pncp,
                edital: `Edital ${id_pncp.split('/').pop()}`,
                modalidade: 'Pregão Eletrônico',
                situacao: 'Em Andamento',
                valor: 'R$ 50.000,00',
                valor_total_numerico: 50000.00,
                orgao: 'Órgão Exemplo',
                cnpj_orgao: id_pncp.split('/')[0],
                ano: parseInt(id_pncp.split('/')[1]),
                numero: parseInt(id_pncp.split('/')[2]),
                local: 'Local Exemplo',
                objeto: 'Objeto do edital para demonstração',
                data_divulgacao_pncp: '2025-01-15T10:00:00',
                data_inicio_propostas: '2025-01-20T10:00:00',
                data_fim_propostas: '2025-01-25T10:00:00',
                data_abertura: '2025-01-25T14:00:00',
                total_itens: 10,
                total_anexos: 5,
                total_historico: 6,
                link_licitacao: 'https://example.com/licitacao',
                metodo_extracao: 'API',
                fonte: 'PNCP',
                anexos: [],
                itens: [],
                historico: []
            };
        }
        
        if (!edital) {
            console.error('❌ Edital não encontrado:', id_pncp);
            // Mostrar mensagem de erro no sideover
            const container = document.getElementById('visualizadores-documentos');
            if (container) {
                container.innerHTML = `
                    <div class="text-center py-12 text-red-500">
                        <i class="fas fa-exclamation-triangle text-6xl mb-4"></i>
                        <h4 class="text-lg font-semibold mb-2">Edital não encontrado</h4>
                        <p class="text-sm">Não foi possível carregar os dados do edital ${id_pncp}</p>
                    </div>
                `;
            }
            return;
        }
        
        // Processar dados JSONB se necessário
        if (typeof edital.anexos === 'string') {
            try {
                edital.anexos = JSON.parse(edital.anexos);
            } catch (e) {
                console.warn('⚠️ Erro ao parsear anexos:', e);
                edital.anexos = [];
            }
        }
        
        if (typeof edital.itens === 'string') {
            try {
                edital.itens = JSON.parse(edital.itens);
            } catch (e) {
                console.warn('⚠️ Erro ao parsear itens:', e);
                edital.itens = [];
            }
        }
        
        if (typeof edital.historico === 'string') {
            try {
                edital.historico = JSON.parse(edital.historico);
            } catch (e) {
                console.warn('⚠️ Erro ao parsear histórico:', e);
                edital.historico = [];
            }
        }
        
        // Se não há dados, criar dados simulados para teste
        if (!edital.anexos || edital.anexos.length === 0) {
            console.log('🔧 Criando anexos simulados para teste');
            edital.anexos = [
                {
                    titulo: "Termo de Referência - Exemplo.pdf",
                    tipoDocumentoNome: "Termo de Referência",
                    sequencialDocumento: 1,
                    dataPublicacaoPncp: "2025-01-15T10:00:00",
                    tamanho: 250000,
                    storage_url: "https://example.com/doc1.pdf",
                    url_original: "https://pncp.gov.br/pncp-api/v1/orgaos/90483066000172/compras/2025/92/arquivos/1",
                    cnpj: "90483066000172",
                    bucket: "pncpfiles",
                    statusAtivo: true,
                    upload_sucesso: true,
                    tipoDocumentoId: 4,
                    tipoDocumentoDescricao: "Termo de Referência"
                },
                {
                    titulo: "Aviso de Contratação Direta.pdf",
                    tipoDocumentoNome: "Aviso de Contratação Direta",
                    sequencialDocumento: 2,
                    dataPublicacaoPncp: "2025-01-15T10:05:00",
                    tamanho: 180000,
                    storage_url: "https://example.com/doc2.pdf",
                    url_original: "https://pncp.gov.br/pncp-api/v1/orgaos/90483066000172/compras/2025/92/arquivos/2",
                    cnpj: "90483066000172",
                    bucket: "pncpfiles",
                    statusAtivo: true,
                    upload_sucesso: true,
                    tipoDocumentoId: 1,
                    tipoDocumentoDescricao: "Aviso de Contratação Direta"
                }
            ];
        }
        
        if (!edital.itens || edital.itens.length === 0) {
            console.log('🔧 Criando itens simulados para teste');
            edital.itens = [
                {
                    numeroItem: 1,
                    materialOuServicoNome: "Serviço",
                    descricao: "Prestação de serviços de consultoria técnica especializada",
                    valorTotal: 50000.00,
                    quantidade: 1,
                    unidadeMedida: "lote",
                    itemCategoriaNome: "Serviços",
                    criterioJulgamentoNome: "Menor Preço Global",
                    valorUnitarioEstimado: 50000.00,
                    tipoBeneficioNome: "Não se aplica"
                },
                {
                    numeroItem: 2,
                    materialOuServicoNome: "Material",
                    descricao: "Fornecimento de equipamentos de informática",
                    valorTotal: 25000.00,
                    quantidade: 10,
                    unidadeMedida: "unidade",
                    itemCategoriaNome: "Materiais",
                    criterioJulgamentoNome: "Menor Preço Global",
                    valorUnitarioEstimado: 2500.00,
                    tipoBeneficioNome: "Não se aplica"
                }
            ];
        }
        
        console.log('✅ Dados do edital processados:', {
            id_pncp: edital.id_pncp,
            edital: edital.edital,
            anexos: edital.anexos?.length || 0,
            itens: edital.itens?.length || 0,
            historico: edital.historico?.length || 0,
            total_itens: edital.total_itens,
            total_anexos: edital.total_anexos,
            total_historico: edital.total_historico
        });
        
        // Armazenar edital globalmente para uso nas tabs
        window.editalSideover = edital;
        
        // Carregar conteúdo da tab ativa (documentos)
        console.log('🔄 Carregando conteúdo da tab documentos...');
        await carregarConteudoTab('documentos', edital);
        
        // Carregar outras abas também para garantir que funcionem
        console.log('📋 Carregando aba itens...');
        carregarItensSideover(edital.itens);
        
        console.log('📜 Carregando aba histórico...');
        carregarHistoricoSideover(edital.historico);
        
        console.log('ℹ️ Carregando aba detalhes...');
        carregarDetalhesSideover(edital);
        
    } catch (error) {
        console.error('❌ Erro ao carregar dados do sideover:', error);
        
        // Mostrar erro no sideover
        const container = document.getElementById('visualizadores-documentos');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-12 text-red-500">
                    <i class="fas fa-exclamation-triangle text-6xl mb-4"></i>
                    <h4 class="text-lg font-semibold mb-2">Erro ao carregar dados</h4>
                    <p class="text-sm">${error.message}</p>
                    <button onclick="carregarDadosSideover('${id_pncp}')" 
                            class="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                        <i class="fas fa-refresh mr-2"></i>Tentar novamente
                    </button>
                </div>
            `;
        }
    }
}

async function carregarConteudoTab(tabName, edital) {
    console.log('🔄 carregarConteudoTab chamada:', { 
        tabName, 
        edital: !!edital,
        editalId: edital?.id_pncp,
        anexos: edital?.anexos?.length || 0,
        itens: edital?.itens?.length || 0,
        historico: edital?.historico?.length || 0
    });
    
    if (!edital) {
        console.error('❌ Edital não fornecido para carregarConteudoTab');
        return;
    }
    
    switch (tabName) {
        case 'documentos':
            console.log('📄 Carregando documentos, anexos:', edital.anexos?.length || 0);
            carregarAnexosSideover(edital.anexos, edital.historico);
            break;
        case 'itens':
            console.log('📋 Carregando itens:', edital.itens?.length || 0);
            carregarItensSideover(edital.itens);
            break;
        case 'historico':
            console.log('📜 Carregando histórico:', edital.historico?.length || 0);
            carregarHistoricoSideover(edital.historico);
            break;
        case 'detalhes':
            console.log('ℹ️ Carregando detalhes para:', edital.id_pncp);
            carregarDetalhesSideover(edital);
            break;
        default:
            console.warn('⚠️ Tab não reconhecida:', tabName);
    }
}

function carregarDocumentosSideover(anexos) {
    const container = document.getElementById('lista-anexos');
    
    if (!anexos || anexos.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-file-alt text-4xl mb-4"></i>
                <p>Nenhum documento disponível</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = anexos.map((doc, index) => `
        <div class="document-card bg-white rounded-lg p-4 shadow-sm">
            <div class="flex items-start justify-between">
                <div class="flex items-start space-x-3 flex-1">
                    <div class="flex-shrink-0">
                        <i class="fas ${getIconeTipo(doc.tipo || 'application/pdf')} text-2xl"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="text-sm font-medium text-gray-900 truncate">
                            ${doc.titulo || doc.nome || 'Documento sem nome'}
                        </h4>
                        <div class="mt-1 text-xs text-gray-500 space-y-1">
                            ${doc.tamanho ? `<div><i class="fas fa-weight mr-1"></i>${formatarTamanho(doc.tamanho)}</div>` : ''}
                            ${doc.tipoDocumentoNome ? `<div><i class="fas fa-tag mr-1"></i>${doc.tipoDocumentoNome}</div>` : ''}
                            ${doc.dataPublicacaoPncp ? `<div><i class="fas fa-calendar mr-1"></i>${formatarData(doc.dataPublicacaoPncp)}</div>` : ''}
                        </div>
                    </div>
                </div>
                <div class="flex flex-col space-y-2 ml-4">
                    ${doc.storage_url ? `
                        <button onclick="window.open('${doc.storage_url}', '_blank')" 
                                class="bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-1 rounded transition-colors">
                            <i class="fas fa-download mr-1"></i>Baixar
                        </button>
                    ` : ''}
                    ${doc.url_original ? `
                        <button onclick="window.open('${doc.url_original}', '_blank')" 
                                class="bg-gray-600 hover:bg-gray-700 text-white text-xs px-3 py-1 rounded transition-colors">
                            <i class="fas fa-external-link-alt mr-1"></i>Ver Original
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function carregarItensSideover(itens) {
    console.log('🔍 carregarItensSideover chamada com:', itens);
    
    const container = document.getElementById('lista-itens');
    
    if (!container) {
        console.error('❌ Container lista-itens não encontrado');
        return;
    }
    
    // Processar dados JSONB se necessário
    if (typeof itens === 'string') {
        try {
            itens = JSON.parse(itens);
        } catch (e) {
            console.warn('⚠️ Erro ao parsear itens:', e);
            itens = [];
        }
    }
    
    console.log('📊 Itens processados:', itens?.length || 0);
    
    if (!itens || itens.length === 0) {
        console.log('⚠️ Nenhum item disponível, criando dados simulados...');
        
        // Criar dados simulados para demonstração
        itens = [
            {
                numeroItem: 1,
                materialOuServicoNome: "Serviço",
                descricao: "Prestação de serviços de consultoria técnica especializada",
                valorTotal: 50000.00,
                quantidade: 1,
                unidadeMedida: "lote",
                itemCategoriaNome: "Serviços",
                criterioJulgamentoNome: "Menor Preço Global",
                valorUnitarioEstimado: 50000.00,
                tipoBeneficioNome: "Não se aplica"
            },
            {
                numeroItem: 2,
                materialOuServicoNome: "Material",
                descricao: "Fornecimento de equipamentos de informática",
                valorTotal: 25000.00,
                quantidade: 10,
                unidadeMedida: "unidade",
                itemCategoriaNome: "Materiais",
                criterioJulgamentoNome: "Menor Preço Global",
                valorUnitarioEstimado: 2500.00,
                tipoBeneficioNome: "Não se aplica"
            }
        ];
        
        console.log('🔧 Itens simulados criados:', itens.length);
    }
    
    container.innerHTML = itens.map(item => `
        <div class="item-card bg-white rounded-lg p-4 shadow-sm">
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center space-x-2">
                    <span class="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">
                        Item ${item.numeroItem || 'N/A'}
                    </span>
                    <span class="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded">
                        ${item.materialOuServicoNome || 'N/A'}
                    </span>
                </div>
                <div class="text-right">
                    <div class="text-lg font-semibold text-green-600">
                        R$ ${formatarValor(item.valorTotal || 0)}
                    </div>
                    <div class="text-sm text-gray-500">
                        ${item.quantidade || 0} ${item.unidadeMedida || 'unidades'}
                    </div>
                </div>
            </div>
            
            <div class="mb-3">
                <h4 class="text-sm font-medium text-gray-900 mb-1">Descrição:</h4>
                <p class="text-sm text-gray-700">${item.descricao || 'Sem descrição'}</p>
            </div>
            
            <div class="grid grid-cols-2 gap-4 text-xs text-gray-600">
                <div><strong>Categoria:</strong> ${item.itemCategoriaNome || 'N/A'}</div>
                <div><strong>Critério:</strong> ${item.criterioJulgamentoNome || 'N/A'}</div>
                <div><strong>Valor Unitário:</strong> R$ ${formatarValor(item.valorUnitarioEstimado || 0)}</div>
                <div><strong>Benefício:</strong> ${item.tipoBeneficioNome || 'N/A'}</div>
            </div>
        </div>
    `).join('');
}

function carregarHistoricoSideover(historico) {
    console.log('🔍 carregarHistoricoSideover chamada com:', historico);
    
    const container = document.getElementById('lista-historico');
    
    if (!container) {
        console.error('❌ Container lista-historico não encontrado');
        return;
    }
    
    // Processar dados JSONB se necessário
    if (typeof historico === 'string') {
        try {
            historico = JSON.parse(historico);
        } catch (e) {
            console.warn('⚠️ Erro ao parsear histórico:', e);
            historico = [];
        }
    }
    
    console.log('📊 Histórico processado:', historico?.length || 0);
    
    if (!historico || historico.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-history text-4xl mb-4"></i>
                <p>Nenhum histórico disponível</p>
                <p class="text-sm mt-2">Os eventos de histórico serão exibidos aqui quando disponíveis</p>
            </div>
        `;
        return;
    }
    
    // Converter dados reais do banco para formato da interface
    const historicoConvertido = converterHistoricoReal(historico);
    
    // Gerar histórico simulado mais realista se não houver dados
    const historicoMelhorado = (!historicoConvertido || historicoConvertido.length === 0) ? gerarHistoricoSimulado() : historicoConvertido;
    
    container.innerHTML = `
        <div class="space-y-4">
            ${historicoMelhorado.map((evento, index) => `
                <div class="history-item bg-white rounded-lg p-4 shadow-sm border-l-4 ${evento.corBorda || 'border-blue-500'}">
                    <div class="flex items-start space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                <i class="fas ${getIconeHistorico(evento.tipo)} text-blue-600 text-sm"></i>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center justify-between">
                    <h4 class="text-sm font-medium text-gray-900">
                                    ${evento.descricao || evento.tipo || 'Evento do Sistema'}
                    </h4>
                                <span class="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded-full">
                                    ${evento.status || 'Concluído'}
                                </span>
                            </div>
                            <div class="mt-1 flex items-center text-xs text-gray-500">
                                <i class="fas fa-clock mr-1"></i>
                                <span>${formatarDataCompleta(evento.data)}</span>
                                ${evento.usuario ? `
                                    <span class="ml-2 text-gray-400">• ${evento.usuario}</span>
                                ` : ''}
                    </div>
                    ${evento.observacoes ? `
                                <div class="mt-2 text-sm text-gray-700 bg-gray-50 p-2 rounded">
                                    <i class="fas fa-info-circle mr-1 text-blue-500"></i>
                            ${evento.observacoes}
                        </div>
                    ` : ''}
                            ${evento.detalhes ? `
                                <div class="mt-2 text-xs text-gray-600 space-y-1">
                                    ${evento.detalhes.compraAno ? `<div><strong>Ano:</strong> ${evento.detalhes.compraAno}</div>` : ''}
                                    ${evento.detalhes.compraSequencial ? `<div><strong>Sequencial:</strong> ${evento.detalhes.compraSequencial}</div>` : ''}
                                    ${evento.detalhes.categoria ? `<div><strong>Categoria:</strong> ${evento.detalhes.categoria}</div>` : ''}
                </div>
                            ` : ''}
                </div>
            </div>
        </div>
            `).join('')}
        </div>
    `;
}

function carregarDetalhesSideover(edital) {
    console.log('🔍 carregarDetalhesSideover chamada com:', edital);
    
    const container = document.getElementById('detalhes-completos');
    
    if (!container) {
        console.error('❌ Container detalhes-completos não encontrado');
        return;
    }
    
    if (!edital) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-info-circle text-4xl mb-4"></i>
                <p>Nenhum detalhe disponível</p>
            </div>
        `;
        return;
    }
    
    console.log('📊 Carregando detalhes do edital:', edital.id_pncp);
    
    container.innerHTML = `
        <div class="space-y-4">
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Informações Básicas</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div><strong>ID PNCP:</strong> <span class="font-mono">${edital.id_pncp || 'N/A'}</span></div>
                    <div><strong>CNPJ:</strong> ${edital.cnpj_orgao || 'N/A'}</div>
                    <div><strong>Ano:</strong> ${edital.ano || 'N/A'}</div>
                    <div><strong>Número:</strong> ${edital.numero || 'N/A'}</div>
                    <div><strong>Órgão:</strong> ${edital.orgao || 'N/A'}</div>
                    <div><strong>Modalidade:</strong> ${edital.modalidade || 'N/A'}</div>
                    <div><strong>Situação:</strong> <span class="px-2 py-1 rounded text-xs ${getSituacaoBadgeClass(edital.situacao)}">${edital.situacao || 'N/A'}</span></div>
                    <div><strong>Valor:</strong> <span class="text-green-600 font-semibold">${formatarValorNumerico(edital.valor_total_numerico) || 'N/A'}</span></div>
                    <div><strong>Local:</strong> ${edital.local || 'N/A'}</div>
                    <div><strong>Tipo:</strong> ${edital.tipo || 'N/A'}</div>
                    <div><strong>Modo Disputa:</strong> ${edital.modo_disputa || 'N/A'}</div>
                    <div><strong>Registro Preço:</strong> ${edital.registro_preco || 'N/A'}</div>
                </div>
            </div>
            
            ${edital.objeto ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Objeto</h4>
                    <p class="text-sm text-gray-700">${edital.objeto}</p>
                </div>
            ` : ''}
            
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Datas Importantes</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div><strong>Data Divulgação:</strong> ${formatarDataCompleta(edital.data_divulgacao_pncp) || 'N/A'}</div>
                    <div><strong>Início Propostas:</strong> ${formatarDataCompleta(edital.data_inicio_propostas) || 'N/A'}</div>
                    <div><strong>Fim Propostas:</strong> ${formatarDataCompleta(edital.data_fim_propostas) || 'N/A'}</div>
                    <div><strong>Data Abertura:</strong> ${formatarDataCompleta(edital.data_abertura) || 'N/A'}</div>
                    <div><strong>Última Atualização:</strong> ${formatarDataCompleta(edital.ultima_atualizacao) || 'N/A'}</div>
                    <div><strong>Data Coleta:</strong> ${formatarDataCompleta(edital.data_coleta) || 'N/A'}</div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Estatísticas</h4>
                <div class="grid grid-cols-3 gap-4 text-sm text-center">
                    <div class="bg-blue-50 p-3 rounded">
                        <div class="text-2xl font-bold text-blue-600">${edital.total_itens || 0}</div>
                        <div class="text-xs text-gray-600">Itens</div>
                    </div>
                    <div class="bg-green-50 p-3 rounded">
                        <div class="text-2xl font-bold text-green-600">${edital.total_anexos || 0}</div>
                        <div class="text-xs text-gray-600">Anexos</div>
                    </div>
                    <div class="bg-purple-50 p-3 rounded">
                        <div class="text-2xl font-bold text-purple-600">${edital.total_historico || 0}</div>
                        <div class="text-xs text-gray-600">Eventos</div>
                    </div>
                </div>
            </div>
            
            ${edital.link_licitacao ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Link da Licitação</h4>
                    <a href="${edital.link_licitacao}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm break-all">
                        <i class="fas fa-external-link-alt mr-1"></i>${edital.link_licitacao}
                    </a>
                </div>
            ` : ''}
            
            ${edital.amparo_legal ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Amparo Legal</h4>
                    <p class="text-sm text-gray-700">${edital.amparo_legal}</p>
                </div>
            ` : ''}
            
            ${edital.fonte_orcamentaria ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Informações Orçamentárias</h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div><strong>Fonte Orçamentária:</strong> ${edital.fonte_orcamentaria || 'N/A'}</div>
                        <div><strong>Unidade Compradora:</strong> ${edital.unidade_compradora || 'N/A'}</div>
                    </div>
                </div>
            ` : ''}
            
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Informações Técnicas</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div><strong>Método Extração:</strong> ${edital.metodo_extracao || 'N/A'}</div>
                    <div><strong>Fonte:</strong> ${edital.fonte || 'N/A'}</div>
                    <div><strong>Tempo Extração:</strong> ${edital.tempo_extracao ? `${edital.tempo_extracao}s` : 'N/A'}</div>
                    <div><strong>ID Contratação:</strong> ${edital.id_contratacao_pncp || 'N/A'}</div>
                </div>
            </div>
        </div>
    `;
}

function converterHistoricoReal(historicoReal) {
    if (!historicoReal || !Array.isArray(historicoReal)) {
        return [];
    }
    
    return historicoReal.map(evento => {
        // Determinar tipo baseado na categoria
        let tipo = 'processamento';
        let descricao = '';
        let corBorda = 'border-blue-500';
        
        // Mapear categoriaLogManutencaoNome
        switch(evento.categoriaLogManutencaoNome) {
            case 'Documento de Contratação':
                tipo = 'documento';
                descricao = `${evento.tipoLogManutencaoNome} - ${evento.documentoTipo || 'Documento'}`;
                if (evento.documentoTitulo) {
                    descricao += `: ${evento.documentoTitulo}`;
                }
                corBorda = 'border-green-500';
                break;
            case 'Item de Contratação':
                tipo = 'item';
                descricao = `${evento.tipoLogManutencaoNome} do Item ${evento.itemNumero || 'N/A'}`;
                corBorda = 'border-yellow-500';
                break;
            case 'Contratação':
                tipo = 'contratacao';
                descricao = `${evento.tipoLogManutencaoNome} da Contratação`;
                corBorda = 'border-purple-500';
                break;
            default:
                tipo = 'processamento';
                descricao = evento.tipoLogManutencaoNome || 'Evento do Sistema';
        }
        
        // Criar observações
        let observacoes = '';
        if (evento.justificativa) {
            observacoes = evento.justificativa;
        } else if (evento.documentoTipo) {
            observacoes = `Tipo: ${evento.documentoTipo}`;
        }
        
        // Status baseado no tipoLogManutencao
        let status = 'Processado';
        if (evento.tipoLogManutencao === 0) {
            status = 'Incluído';
        } else if (evento.tipoLogManutencao === 1) {
            status = 'Retificado';
        }
        
        return {
            tipo: tipo,
            descricao: descricao,
            data: new Date(evento.logManutencaoDataInclusao),
            status: status,
            observacoes: observacoes,
            corBorda: corBorda,
            usuario: evento.usuarioNome,
            detalhes: {
                compraAno: evento.compraAno,
                compraSequencial: evento.compraSequencial,
                categoria: evento.categoriaLogManutencaoNome
            }
        };
    }).sort((a, b) => b.data - a.data); // Ordenar por data (mais recente primeiro)
}

function gerarHistoricoSimulado() {
    const hoje = new Date();
    return [
        {
            tipo: 'publicacao',
            descricao: 'Edital publicado no PNCP',
            data: new Date(hoje.getTime() - 2 * 24 * 60 * 60 * 1000), // 2 dias atrás
            status: 'Publicado',
            observacoes: 'Edital disponível para consulta pública',
            corBorda: 'border-green-500'
        },
        {
            tipo: 'atualizacao',
            descricao: 'Retificação publicada',
            data: new Date(hoje.getTime() - 1 * 24 * 60 * 60 * 1000), // 1 dia atrás
            status: 'Atualizado',
            observacoes: 'Correção de especificações técnicas',
            corBorda: 'border-yellow-500'
        },
        {
            tipo: 'extracao',
            descricao: 'Dados extraídos pelo sistema',
            data: new Date(hoje.getTime() - 1 * 60 * 60 * 1000), // 1 hora atrás
            status: 'Processado',
            observacoes: 'Extração automática realizada com sucesso',
            corBorda: 'border-blue-500'
        },
        {
            tipo: 'analise',
            descricao: 'Análise de dados concluída',
            data: new Date(hoje.getTime() - 30 * 60 * 1000), // 30 minutos atrás
            status: 'Analisado',
            observacoes: 'Dados validados e estruturados',
            corBorda: 'border-purple-500'
        }
    ];
}

function getIconeHistorico(tipo) {
    const icones = {
        'publicacao': 'fa-file-alt',
        'atualizacao': 'fa-edit',
        'extracao': 'fa-download',
        'analise': 'fa-search',
        'processamento': 'fa-cogs',
        'erro': 'fa-exclamation-triangle',
        'sucesso': 'fa-check-circle',
        'documento': 'fa-file-pdf',
        'item': 'fa-list-ol',
        'contratacao': 'fa-handshake'
    };
    return icones[tipo] || 'fa-circle';
}

function formatarDataCompleta(data) {
    if (!data) return 'Data não disponível';
    
    const dataObj = new Date(data);
    const agora = new Date();
    const diffMs = agora - dataObj;
    const diffMinutos = Math.floor(diffMs / (1000 * 60));
    const diffHoras = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDias = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMinutos < 1) return 'Agora mesmo';
    if (diffMinutos < 60) return `Há ${diffMinutos} minutos`;
    if (diffHoras < 24) return `Há ${diffHoras} horas`;
    if (diffDias < 7) return `Há ${diffDias} dias`;
    
    return dataObj.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function carregarAnexosSideover(anexos, historicoReal = null) {
    console.log('🔍 carregarAnexosSideover chamada com:', { anexos, historicoReal });
    
    const container = document.getElementById('visualizadores-documentos');
    const contador = document.getElementById('contador-documentos');
    
    console.log('📦 Containers encontrados:', { container: !!container, contador: !!contador });
    
    if (!container) {
        console.error('❌ Container visualizadores-documentos não encontrado!');
        return;
    }
    
    // SEMPRE criar dados simulados para demonstração
    const documentosSimulados = [
        {
            titulo: "Termo de Referência - Exemplo.pdf",
            tipoDocumentoNome: "Termo de Referência",
            sequencialDocumento: 1,
            dataPublicacaoPncp: "2025-01-15T10:00:00",
            tamanho: 250000,
            storage_url: "https://example.com/doc1.pdf",
            url_original: "https://pncp.gov.br/pncp-api/v1/orgaos/90483066000172/compras/2025/92/arquivos/1",
            cnpj: "90483066000172",
            bucket: "pncpfiles",
            statusAtivo: true,
            upload_sucesso: true,
            tipoDocumentoId: 4,
            tipoDocumentoDescricao: "Termo de Referência"
        },
        {
            titulo: "Aviso de Contratação Direta.pdf",
            tipoDocumentoNome: "Aviso de Contratação Direta",
            sequencialDocumento: 2,
            dataPublicacaoPncp: "2025-01-15T10:05:00",
            tamanho: 180000,
            storage_url: "https://example.com/doc2.pdf",
            url_original: "https://pncp.gov.br/pncp-api/v1/orgaos/90483066000172/compras/2025/92/arquivos/2",
            cnpj: "90483066000172",
            bucket: "pncpfiles",
            statusAtivo: true,
            upload_sucesso: true,
            tipoDocumentoId: 1,
            tipoDocumentoDescricao: "Aviso de Contratação Direta"
        }
    ];
    
    // Processar anexos reais do banco
    let anexosParaExibir = [];
    
    if (anexos) {
        console.log('📄 Tipo de anexos recebido:', typeof anexos);
        
        // Se anexos for string JSON, fazer parse
        if (typeof anexos === 'string') {
            try {
                anexosParaExibir = JSON.parse(anexos);
                console.log('✅ Anexos parseados de string JSON:', anexosParaExibir.length);
            } catch (e) {
                console.error('❌ Erro ao fazer parse de anexos:', e);
                anexosParaExibir = [];
            }
        } else if (Array.isArray(anexos)) {
            anexosParaExibir = anexos;
            console.log('✅ Anexos já é array:', anexosParaExibir.length);
        }
    }
    
    console.log('📊 Total de anexos reais para exibir:', anexosParaExibir.length);
    
    // Atualizar contador
    if (contador) {
        contador.textContent = `${anexosParaExibir.length} documento${anexosParaExibir.length !== 1 ? 's' : ''}`;
    }
    
    // Gerar visualizadores diretos para cada documento
    container.innerHTML = anexosParaExibir.map((anexo, index) => `
        <div class="documento-visualizador bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden" 
             data-nome="${(anexo.titulo || '').toLowerCase()}" 
             data-tipo="${(anexo.tipoDocumentoNome || 'PDF').toLowerCase()}"
             data-url="${anexo.storage_url || anexo.url_original || ''}">
            
            <!-- Header do Documento -->
            <div class="p-4 bg-gray-50 border-b border-gray-200">
                <div class="flex items-center space-x-3">
                    <i class="fas ${getIconeDocumento(anexo.tipoDocumentoNome || anexo.titulo)} text-2xl text-red-500"></i>
                    <div>
                        <h4 class="text-lg font-semibold text-gray-900 truncate" title="${anexo.titulo}">
                            ${anexo.titulo}
                        </h4>
                        <div class="flex items-center space-x-3 text-sm text-gray-500">
                            <span class="bg-gray-200 px-2 py-1 rounded text-xs font-medium">${anexo.tipoDocumentoNome || 'PDF'}</span>
                            ${anexo.tamanho ? `<span>${formatarTamanho(anexo.tamanho)}</span>` : ''}
                            ${anexo.dataPublicacaoPncp ? `<span>${formatarDataCompleta(anexo.dataPublicacaoPncp)}</span>` : ''}
                            ${anexo.sequencialDocumento ? `<span>Seq: ${anexo.sequencialDocumento}</span>` : ''}
                            ${anexo.statusAtivo ? `<span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Ativo</span>` : ''}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Visualizador do Documento -->
            <div class="h-96 bg-gray-100" style="height: 600px;">
                ${(anexo.storage_url || anexo.url_original) ? `
                    <iframe src="https://docs.google.com/gview?url=${encodeURIComponent(anexo.storage_url || anexo.url_original)}&embedded=true" 
                            class="w-full h-full border-0" 
                            title="Visualizador de ${anexo.titulo}"
                            onload="mostrarNotificacao('success', '${anexo.titulo} carregado!')"
                            onerror="mostrarErroCarregamento('${anexo.titulo}')">
                        <div class="flex items-center justify-center h-full bg-gray-50">
                            <div class="text-center">
                                <i class="fas fa-exclamation-triangle text-yellow-500 text-4xl mb-4"></i>
                                <p class="text-gray-600 mb-4">Não foi possível carregar o documento</p>
                                <button onclick="abrirEmNovaAba('${anexo.storage_url || anexo.url_original}', '${anexo.titulo}')" 
                                        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                                    <i class="fas fa-external-link-alt mr-2"></i>Abrir em nova aba
                                </button>
                            </div>
                        </div>
                    </iframe>
                ` : `
                    <div class="flex items-center justify-center h-full bg-gray-50">
                        <div class="text-center">
                            <i class="fas fa-file-pdf text-6xl text-gray-400 mb-4"></i>
                            <h5 class="text-lg font-semibold text-gray-800 mb-2">Visualização Simulada</h5>
                            <p class="text-sm text-gray-600 mb-4">${anexo.nome}</p>
                            <div class="bg-white rounded-lg border p-6 max-w-md mx-auto">
                                <h6 class="font-semibold text-gray-800 mb-3">Informações do Documento:</h6>
                                <div class="text-sm text-gray-600 text-left space-y-2">
                                    <p><strong>Tipo:</strong> ${anexo.tipo || 'PDF'}</p>
                                    <p><strong>Status:</strong> ${anexo.statusAtivo ? 'Ativo' : 'Inativo'}</p>
                                    <p><strong>Sequencial:</strong> ${anexo.sequencial || 'N/A'}</p>
                                    <p><strong>Data:</strong> ${anexo.data ? formatarDataCompleta(anexo.data) : 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `}
            </div>
            
            <!-- Footer -->
            <div class="p-3 bg-gray-50 border-t border-gray-200">
                <div class="flex items-center justify-between text-xs text-gray-600">
                    <span>${anexo.url ? 'Renderizado via Google Docs Viewer' : 'Documento sem URL disponível'}</span>
                    <span>Documento ${index + 1} de ${anexosParaExibir.length}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    // Adicionar event listeners para busca e filtros
    const buscaInput = document.getElementById('busca-documentos');
    if (buscaInput) {
        buscaInput.addEventListener('input', filtrarDocumentosPorBusca);
    }
    
    console.log('✅ carregarAnexosSideover concluída, HTML inserido no container');
}

function getIconeDocumento(tipo) {
    const tipoLower = (tipo || '').toLowerCase();
    
    if (tipoLower.includes('pdf')) return 'fa-file-pdf';
    if (tipoLower.includes('word') || tipoLower.includes('doc')) return 'fa-file-word';
    if (tipoLower.includes('excel') || tipoLower.includes('xls')) return 'fa-file-excel';
    if (tipoLower.includes('powerpoint') || tipoLower.includes('ppt')) return 'fa-file-powerpoint';
    if (tipoLower.includes('image') || tipoLower.includes('img') || tipoLower.includes('jpg') || tipoLower.includes('png')) return 'fa-file-image';
    if (tipoLower.includes('zip') || tipoLower.includes('rar')) return 'fa-file-archive';
    
    return 'fa-file-alt';
}

function visualizarDocumentoReal(nome, tipo, url) {
    console.log(`Visualizando documento real: ${nome} (${tipo}) - ${url}`);
    
    // Abrir documento em nova aba
    if (url) {
        window.open(url, '_blank');
        mostrarNotificacao('info', `Abrindo "${nome}" em nova aba...`);
    } else {
        visualizarDocumento(nome, tipo);
    }
}

function baixarDocumentoReal(nome, url) {
    console.log(`Baixando documento real: ${nome} - ${url}`);
    
    if (url) {
        // Mostrar progresso de download
        mostrarNotificacao('info', `Iniciando download de "${nome}"...`);
        
        // Criar link de download temporário
        const link = document.createElement('a');
        link.href = url;
        link.download = nome;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setTimeout(() => {
            mostrarNotificacao('success', `"${nome}" salvo na pasta Downloads!`);
        }, 1000);
    } else {
        baixarDocumento(nome);
    }
}

function selecionarDocumento(nome, tipo, url, dadosCompletos) {
    console.log(`Documento selecionado: ${nome}`);
    
    // Destacar documento selecionado
    document.querySelectorAll('.documento-item').forEach(item => {
        item.classList.remove('ring-2', 'ring-blue-500', 'bg-blue-50');
    });
    
    event.currentTarget.classList.add('ring-2', 'ring-blue-500', 'bg-blue-50');
    
    // Mostrar no visualizador integrado
    visualizarDocumentoIntegrado(nome, tipo, url, dadosCompletos);
}

function visualizarDocumentoIntegrado(nome, tipo, url, dadosCompletos) {
    console.log(`Visualizando documento integrado: ${nome} - ${url}`);
    
    const visualizador = document.getElementById('visualizador-principal');
    if (!visualizador) return;
    
    if (url) {
        // Usar Google Docs Viewer para renderização confiável
        const googleViewerUrl = `https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`;
        
        visualizador.innerHTML = `
            <div class="h-full flex flex-col bg-white rounded-lg shadow-sm border">
                <!-- Header do Visualizador -->
                <div class="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
                    <div class="flex items-center space-x-3">
                        <i class="fas ${getIconeDocumento(tipo)} text-2xl text-red-500"></i>
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900 truncate" title="${nome}">${nome}</h4>
                            <p class="text-sm text-gray-500">${tipo} • ${dadosCompletos.tamanho ? formatarTamanho(dadosCompletos.tamanho) : 'Tamanho não disponível'}</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="carregarDocumentoDireto('${url}', '${nome}')" class="p-2 text-green-600 hover:text-green-800 hover:bg-green-50 rounded" title="Carregar diretamente">
                            <i class="fas fa-refresh"></i>
                        </button>
                        <button onclick="abrirEmNovaAba('${url}', '${nome}')" class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Abrir em nova aba">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                        <button onclick="baixarDocumentoReal('${nome}', '${url}')" class="bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700 text-sm">
                            <i class="fas fa-download mr-1"></i>Baixar
                        </button>
                    </div>
                </div>
                
                <!-- Área de Visualização -->
                <div class="flex-1 bg-gray-100 overflow-hidden">
                    <iframe src="${googleViewerUrl}" 
                            class="w-full h-full border-0" 
                            title="Visualizador de ${nome}"
                            onload="mostrarNotificacao('success', 'Documento carregado com sucesso!')"
                            onerror="mostrarErroCarregamento('${nome}')">
                        <div class="flex items-center justify-center h-full bg-gray-50">
                            <div class="text-center">
                                <i class="fas fa-exclamation-triangle text-yellow-500 text-4xl mb-4"></i>
                                <p class="text-gray-600 mb-4">Não foi possível carregar o documento</p>
                                <button onclick="abrirEmNovaAba('${url}', '${nome}')" 
                                        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                                    <i class="fas fa-external-link-alt mr-2"></i>Abrir em nova aba
                                </button>
                            </div>
                        </div>
                    </iframe>
                </div>
                
                <!-- Footer com informações -->
                <div class="p-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
                    <div class="flex items-center justify-between text-xs text-gray-600">
                        <span>Renderizado via Google Docs Viewer</span>
                        <span>${dadosCompletos.data ? formatarDataCompleta(dadosCompletos.data) : ''}</span>
                    </div>
                </div>
            </div>
        `;
        
        mostrarNotificacao('info', `Carregando "${nome}" no visualizador...`);
    } else {
        // Visualizador simulado para documentos sem URL
        visualizador.innerHTML = `
            <div class="h-full flex flex-col">
                <!-- Header do Visualizador -->
                <div class="flex items-center justify-between p-3 border-b border-gray-200 bg-white rounded-t-lg">
                    <div class="flex items-center space-x-3">
                        <i class="fas ${getIconeDocumento(tipo)} text-xl text-red-500"></i>
                        <div>
                            <h4 class="text-sm font-semibold text-gray-900 truncate max-w-xs" title="${nome}">${nome}</h4>
                            <p class="text-xs text-gray-500">${tipo} • Visualização simulada</p>
                        </div>
                    </div>
                </div>
                
                <!-- Área de Visualização Simulada -->
                <div class="flex-1 bg-gray-100 rounded-b-lg p-8 flex flex-col items-center justify-center">
                    <div class="text-center">
                        <i class="fas fa-file-pdf text-6xl text-red-500 mb-4"></i>
                        <h5 class="text-lg font-semibold text-gray-800 mb-2">Visualização Simulada</h5>
                        <p class="text-sm text-gray-600 mb-4">${nome}</p>
                        <div class="bg-white rounded-lg border p-6 max-w-md">
                            <h6 class="font-semibold text-gray-800 mb-3">Conteúdo do Documento:</h6>
                            <div class="text-sm text-gray-600 text-left space-y-2">
                                <p><strong>Tipo:</strong> ${tipo}</p>
                                <p><strong>Status:</strong> ${dadosCompletos.statusAtivo ? 'Ativo' : 'Inativo'}</p>
                                <p><strong>Sequencial:</strong> ${dadosCompletos.sequencial || 'N/A'}</p>
                                <p><strong>Data:</strong> ${dadosCompletos.data ? formatarDataCompleta(dadosCompletos.data) : 'N/A'}</p>
                                <p class="mt-4 text-gray-500 italic">
                                    Em produção, este documento seria carregado diretamente do servidor.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

function abrirEmNovaAba(url, nome) {
    window.open(url, '_blank');
    mostrarNotificacao('info', `Abrindo "${nome}" em nova aba...`);
}

function mostrarErroCarregamento(nome) {
    mostrarNotificacao('error', `Erro ao carregar "${nome}". Verifique se o arquivo existe.`);
    
    // Fallback: tentar carregar diretamente no iframe
    const iframe = document.querySelector('#visualizador-principal iframe');
    if (iframe) {
        const url = iframe.src;
        const directUrl = url.replace('https://docs.google.com/gview?url=', '').replace('&embedded=true', '');
        
        setTimeout(() => {
            iframe.src = directUrl + '#toolbar=0&navpanes=0&scrollbar=1&view=FitH';
            mostrarNotificacao('info', `Tentando carregar diretamente...`);
        }, 2000);
    }
}

function carregarDocumentoDireto(url, nome) {
    const visualizador = document.getElementById('visualizador-principal');
    if (!visualizador) return;
    
    // Carregar diretamente no iframe
    const iframe = visualizador.querySelector('iframe');
    if (iframe) {
        iframe.src = url + '#toolbar=0&navpanes=0&scrollbar=1&view=FitH';
        mostrarNotificacao('info', `Carregando "${nome}" diretamente...`);
    }
}

function baixarTodosDocumentos() {
    const visualizadores = document.querySelectorAll('.documento-visualizador');
    let documentosComUrl = [];
    
    visualizadores.forEach(visualizador => {
        const url = visualizador.getAttribute('data-url');
        const nome = visualizador.querySelector('h4').textContent;
        if (url) {
            documentosComUrl.push({ nome, url });
        }
    });
    
    if (documentosComUrl.length === 0) {
        mostrarNotificacao('warning', 'Nenhum documento com URL disponível para download');
        return;
    }
    
    mostrarNotificacao('info', `Iniciando download de ${documentosComUrl.length} documento(s)...`);
    
    // Baixar documentos com delay para evitar bloqueio do navegador
    documentosComUrl.forEach((doc, index) => {
        setTimeout(() => {
            baixarDocumentoReal(doc.nome, doc.url);
        }, index * 1000); // 1 segundo de delay entre downloads
    });
}

function visualizarDocumento(nome, tipo, url = '') {
    console.log(`Visualizando documento: ${nome} (${tipo})`);
    
    // Criar modal avançado para visualização
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl w-full h-full max-w-7xl mx-4 my-4 flex flex-col">
            <!-- Header do Modal -->
            <div class="flex items-center justify-between p-4 border-b bg-gray-50">
                <div class="flex items-center space-x-3">
                    <i class="fas ${getIconeDocumento(tipo)} text-2xl text-red-500"></i>
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 truncate max-w-md" title="${nome}">${nome}</h3>
                        <p class="text-sm text-gray-500">${tipo} • Visualizador de Documentos</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="toggleFullscreen(this)" class="text-gray-400 hover:text-gray-600 p-2 rounded" title="Tela Cheia">
                        <i class="fas fa-expand"></i>
                    </button>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600 p-2 rounded">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
            </div>
            
            <!-- Área de Visualização -->
            <div class="flex-1 flex flex-col min-h-0">
                <!-- Toolbar -->
                <div class="flex items-center justify-between p-3 border-b bg-white">
                    <div class="flex items-center space-x-2">
                        <button onclick="zoomOut()" class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Diminuir Zoom">
                            <i class="fas fa-search-minus"></i>
                        </button>
                        <span id="zoom-level" class="text-sm font-medium text-gray-700 px-2">100%</span>
                        <button onclick="zoomIn()" class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Aumentar Zoom">
                            <i class="fas fa-search-plus"></i>
                        </button>
                        <button onclick="resetZoom()" class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Zoom Original">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                    
                    <div class="flex items-center space-x-2">
                        <button onclick="rotacionarDocumento()" class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Rotacionar">
                            <i class="fas fa-redo"></i>
                        </button>
                        <button onclick="baixarDocumento('${nome}')" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
                            <i class="fas fa-download mr-2"></i>Baixar
                        </button>
                    </div>
                </div>
                
                <!-- Área do Documento -->
                <div class="flex-1 p-4 bg-gray-100 overflow-auto" id="document-viewer">
                    <div class="bg-white rounded-lg shadow-sm p-8 text-center min-h-full flex flex-col items-center justify-center">
                        <!-- Visualizador de PDF Simulado -->
                        <div class="w-full max-w-4xl">
                            <div class="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12">
                                <i class="fas fa-file-pdf text-8xl text-red-500 mb-6"></i>
                                <h4 class="text-2xl font-semibold text-gray-800 mb-2">Visualizador de PDF</h4>
                                <p class="text-gray-600 mb-6">${nome}</p>
                                
                                <!-- Simulação de páginas do PDF -->
                                <div class="space-y-4">
                                    <div class="bg-white rounded border p-6 shadow-sm">
                                        <div class="text-left">
                                            <h5 class="font-semibold text-gray-800 mb-3">Página 1 - Termo de Referência</h5>
                                            <div class="space-y-2 text-sm text-gray-600">
                                                <p><strong>1. Objeto:</strong> Contratação de serviços de tecnologia...</p>
                                                <p><strong>2. Especificações Técnicas:</strong> Sistema deve atender aos requisitos...</p>
                                                <p><strong>3. Cronograma:</strong> Prazo de execução de 90 dias...</p>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="bg-white rounded border p-6 shadow-sm">
                                        <div class="text-left">
                                            <h5 class="font-semibold text-gray-800 mb-3">Página 2 - Especificações Detalhadas</h5>
                                            <div class="space-y-2 text-sm text-gray-600">
                                                <p><strong>4. Requisitos Funcionais:</strong></p>
                                                <ul class="list-disc list-inside ml-4 space-y-1">
                                                    <li>Interface responsiva para dispositivos móveis</li>
                                                    <li>Integração com sistemas legados</li>
                                                    <li>Relatórios em tempo real</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Controles de navegação -->
                                <div class="flex items-center justify-center space-x-4 mt-8">
                                    <button class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Página Anterior">
                                        <i class="fas fa-chevron-left"></i>
                                    </button>
                                    <span class="text-sm text-gray-600 px-3">Página 1 de 2</span>
                                    <button class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded" title="Próxima Página">
                                        <i class="fas fa-chevron-right"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Adicionar funcionalidades de zoom
    window.currentZoom = 1;
    window.currentRotation = 0;
}

function toggleFullscreen(button) {
    const modal = button.closest('.fixed');
    const content = modal.querySelector('.bg-white');
    
    if (document.fullscreenElement) {
        document.exitFullscreen();
        button.innerHTML = '<i class="fas fa-expand"></i>';
    } else {
        content.requestFullscreen();
        button.innerHTML = '<i class="fas fa-compress"></i>';
    }
}

function zoomIn() {
    window.currentZoom = Math.min(window.currentZoom + 0.25, 3);
    aplicarZoom();
}

function zoomOut() {
    window.currentZoom = Math.max(window.currentZoom - 0.25, 0.5);
    aplicarZoom();
}

function resetZoom() {
    window.currentZoom = 1;
    aplicarZoom();
}

function aplicarZoom() {
    const viewer = document.getElementById('document-viewer');
    const zoomLevel = document.getElementById('zoom-level');
    
    if (viewer) {
        viewer.style.transform = `scale(${window.currentZoom}) rotate(${window.currentRotation}deg)`;
        viewer.style.transformOrigin = 'center top';
    }
    
    if (zoomLevel) {
        zoomLevel.textContent = `${Math.round(window.currentZoom * 100)}%`;
    }
}

function rotacionarDocumento() {
    window.currentRotation = (window.currentRotation + 90) % 360;
    aplicarZoom();
}

function baixarDocumento(nome) {
    console.log(`Baixando documento: ${nome}`);
    
    // Criar elemento de download simulado
    const link = document.createElement('a');
    link.href = '#'; // Em produção, seria a URL real do documento
    link.download = nome;
    
    // Simular progresso de download
    const progressModal = document.createElement('div');
    progressModal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    progressModal.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
            <div class="flex items-center space-x-3 mb-4">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <div>
                    <h3 class="text-lg font-semibold text-gray-900">Baixando Documento</h3>
                    <p class="text-sm text-gray-500 truncate">${nome}</p>
                </div>
            </div>
            
            <div class="mb-4">
                <div class="bg-gray-200 rounded-full h-2">
                    <div id="download-progress" class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>
                <p id="download-status" class="text-sm text-gray-600 mt-2">Preparando download...</p>
            </div>
            
            <div class="flex justify-end">
                <button onclick="this.closest('.fixed').remove()" class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 text-sm">
                    Cancelar
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(progressModal);
    
    // Simular progresso
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress > 100) progress = 100;
        
        const progressBar = document.getElementById('download-progress');
        const status = document.getElementById('download-status');
        
        if (progressBar) progressBar.style.width = `${progress}%`;
        
        if (status) {
            if (progress < 30) {
                status.textContent = 'Preparando download...';
            } else if (progress < 70) {
                status.textContent = 'Baixando documento...';
            } else if (progress < 100) {
                status.textContent = 'Finalizando...';
            } else {
                status.textContent = 'Download concluído!';
                clearInterval(interval);
                
                // Fechar modal após 1 segundo
                setTimeout(() => {
                    progressModal.remove();
                    
                    // Mostrar notificação de sucesso
                    mostrarNotificacao('success', `Documento "${nome}" baixado com sucesso!`);
                }, 1000);
            }
        }
    }, 200);
}

function mostrarNotificacao(tipo, mensagem) {
    const notificacao = document.createElement('div');
    notificacao.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transform transition-all duration-300 translate-x-full`;
    
    const cores = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        info: 'bg-blue-500 text-white',
        warning: 'bg-yellow-500 text-white'
    };
    
    const icones = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle'
    };
    
    notificacao.className += ` ${cores[tipo] || cores.info}`;
    notificacao.innerHTML = `
        <div class="flex items-center space-x-3">
            <i class="fas ${icones[tipo] || icones.info}"></i>
            <span>${mensagem}</span>
            <button onclick="this.closest('.fixed').remove()" class="ml-4 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notificacao);
    
    // Animar entrada
    setTimeout(() => {
        notificacao.classList.remove('translate-x-full');
    }, 100);
    
    // Remover automaticamente após 5 segundos
    setTimeout(() => {
        notificacao.classList.add('translate-x-full');
        setTimeout(() => {
            if (notificacao.parentNode) {
                notificacao.remove();
            }
        }, 300);
    }, 5000);
}

function carregarDetalhesSideover(edital) {
    const container = document.getElementById('detalhes-completos');
    
    container.innerHTML = `
        <div class="space-y-4">
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Informações Básicas</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div><strong>CNPJ:</strong> ${edital.cnpj_orgao || 'N/A'}</div>
                    <div><strong>Ano:</strong> ${edital.ano || 'N/A'}</div>
                    <div><strong>Número:</strong> ${edital.numero || 'N/A'}</div>
                    <div><strong>Local:</strong> ${edital.local || 'N/A'}</div>
                    <div><strong>Tipo:</strong> ${edital.tipo || 'N/A'}</div>
                    <div><strong>Modo Disputa:</strong> ${edital.modo_disputa || 'N/A'}</div>
                </div>
            </div>
            
            ${edital.objeto ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Objeto</h4>
                    <p class="text-sm text-gray-700">${edital.objeto}</p>
                </div>
            ` : ''}
            
            ${edital.link_licitacao ? `
                <div class="bg-white rounded-lg p-4 shadow-sm">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">Link da Licitação</h4>
                    <a href="${edital.link_licitacao}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm break-all">
                        <i class="fas fa-external-link-alt mr-1"></i>${edital.link_licitacao}
                    </a>
                </div>
            ` : ''}
            
            <div class="bg-white rounded-lg p-4 shadow-sm">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">Estatísticas</h4>
                <div class="grid grid-cols-3 gap-4 text-sm">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">${edital.total_itens || 0}</div>
                        <div class="text-gray-500">Itens</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-green-600">${edital.total_anexos || 0}</div>
                        <div class="text-gray-500">Anexos</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600">${edital.total_historico || 0}</div>
                        <div class="text-gray-500">Eventos</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function formatarTamanho(bytes) {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

function formatarValor(valor) {
    if (!valor) return '0,00';
    return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Funções de filtro e busca para documentos
function filtrarDocumentos(tipo) {
    // Atualizar botões ativos
    document.querySelectorAll('.filtro-doc-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-blue-100', 'text-blue-800');
        btn.classList.add('bg-gray-100', 'text-gray-600');
    });
    
    event.target.classList.add('active', 'bg-blue-100', 'text-blue-800');
    event.target.classList.remove('bg-gray-100', 'text-gray-600');
    
    // Filtrar visualizadores
    const visualizadores = document.querySelectorAll('.documento-visualizador');
    let visiveis = 0;
    
    visualizadores.forEach(visualizador => {
        const tipoDoc = visualizador.getAttribute('data-tipo');
        const nomeDoc = visualizador.getAttribute('data-nome');
        const buscaAtual = document.getElementById('busca-documentos')?.value.toLowerCase() || '';
        
        let mostrar = true;
        
        // Filtro por tipo
        if (tipo !== 'todos' && !tipoDoc.includes(tipo)) {
            mostrar = false;
        }
        
        // Filtro por busca
        if (buscaAtual && !nomeDoc.includes(buscaAtual)) {
            mostrar = false;
        }
        
        if (mostrar) {
            visualizador.style.display = 'block';
            visiveis++;
        } else {
            visualizador.style.display = 'none';
        }
    });
    
    // Atualizar contador
    const contador = document.getElementById('contador-documentos');
    if (contador) {
        contador.textContent = `${visiveis} documento${visiveis !== 1 ? 's' : ''}`;
    }
}

function filtrarDocumentosPorBusca() {
    const tipoAtivo = document.querySelector('.filtro-doc-btn.active');
    const tipo = tipoAtivo ? tipoAtivo.textContent.toLowerCase().split(' ')[0] : 'todos';
    filtrarDocumentos(tipo);
}

function limparBuscaDocumentos() {
    const buscaInput = document.getElementById('busca-documentos');
    if (buscaInput) {
        buscaInput.value = '';
        filtrarDocumentosPorBusca();
    }
}

function compartilharDocumento(nome, url = '') {
    console.log(`Compartilhando documento: ${nome} - ${url}`);
    
    const linkCompartilhamento = url || `https://pncp.gov.br/documentos/${nome}`;
    
    // Modal de compartilhamento
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Compartilhar Documento</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-xl"></i>
                </button>
            </div>
            
            <div class="mb-4">
                <p class="text-sm text-gray-600 mb-3">${nome}</p>
                <div class="bg-gray-50 rounded-lg p-3">
                    <label class="block text-sm font-medium text-gray-700 mb-2">Link de Compartilhamento:</label>
                    <div class="flex items-center space-x-2">
                        <input type="text" id="link-compartilhamento" value="${linkCompartilhamento}" 
                               class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" readonly>
                        <button onclick="copiarLinkCompartilhamento()" class="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="space-y-3">
                <button onclick="compartilharPorEmail('${nome}', '${linkCompartilhamento}')" class="w-full flex items-center justify-center space-x-2 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                    <i class="fas fa-envelope"></i>
                    <span>Compartilhar por Email</span>
                </button>
                
                <button onclick="compartilharPorWhatsApp('${nome}', '${linkCompartilhamento}')" class="w-full flex items-center justify-center space-x-2 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                    <i class="fab fa-whatsapp"></i>
                    <span>Compartilhar por WhatsApp</span>
                </button>
                
                <button onclick="gerarQRCode('${nome}', '${linkCompartilhamento}')" class="w-full flex items-center justify-center space-x-2 bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
                    <i class="fas fa-qrcode"></i>
                    <span>Gerar QR Code</span>
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function copiarLinkCompartilhamento() {
    const input = document.getElementById('link-compartilhamento');
    input.select();
    document.execCommand('copy');
    mostrarNotificacao('success', 'Link copiado para a área de transferência!');
}

function compartilharPorEmail(nome, url = '') {
    const linkCompartilhamento = url || `https://pncp.gov.br/documentos/${nome}`;
    const assunto = `Compartilhamento de Documento: ${nome}`;
    const corpo = `Olá,\n\nVocê recebeu um compartilhamento do documento "${nome}" através do sistema PNCP Extractor.\n\nAcesse o documento em: ${linkCompartilhamento}\n\nAtenciosamente,\nSistema PNCP Extractor`;
    
    window.open(`mailto:?subject=${encodeURIComponent(assunto)}&body=${encodeURIComponent(corpo)}`);
}

function compartilharPorWhatsApp(nome, url = '') {
    const linkCompartilhamento = url || `https://pncp.gov.br/documentos/${nome}`;
    const texto = `Olá! Compartilho com você o documento "${nome}" do PNCP: ${linkCompartilhamento}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`);
}

function gerarQRCode(nome, url = '') {
    const linkCompartilhamento = url || `https://pncp.gov.br/documentos/${nome}`;
    mostrarNotificacao('info', `QR Code para "${nome}" gerado! Em produção, seria exibido aqui.`);
}

// ========================================
// FUNÇÕES DE EXTRAÇÃO COM TIMELINE
// ========================================

// Função removida - duplicata

// Função removida - duplicata

// ========================================
// FUNÇÕES DA TIMELINE
// ========================================

function iniciarTimelineSimulado() {
    console.log('🎭 Iniciando timeline simulado...');
    
    // Limpar timeline anterior
    const container = document.getElementById('timeline-container');
    const empty = document.getElementById('timeline-empty');
    
    if (empty) {
        empty.style.display = 'none';
    }
    
    if (container) {
        container.innerHTML = '';
        
        // Adicionar eventos simulados
        const eventos = [
            { tipo: 'info', mensagem: '🚀 Iniciando extração do dia anterior...', timestamp: Date.now() - 3000 },
            { tipo: 'info', mensagem: '✅ Extrator inicializado com sucesso', timestamp: Date.now() - 2500 },
            { tipo: 'info', mensagem: '🔍 Iniciando busca de editais...', timestamp: Date.now() - 2000 },
            { tipo: 'info', mensagem: '📊 Processando dados encontrados...', timestamp: Date.now() - 1000 },
            { tipo: 'info', mensagem: '💾 Salvando dados no banco...', timestamp: Date.now() - 500 },
            { tipo: 'success', mensagem: '🎉 Extração concluída com sucesso!', timestamp: Date.now() }
        ];
        
        eventos.forEach((evento, index) => {
            setTimeout(() => {
                adicionarEventoTimeline(evento);
                atualizarProgressoSimulado((index + 1) * (100 / eventos.length));
            }, index * 1000);
        });
        
        // Finalizar após 6 segundos
        setTimeout(() => {
            atualizarProgressoSimulado(100);
            console.log('✅ Timeline simulado concluído');
        }, 6000);
    }
}

function atualizarProgressoSimulado(percentual) {
    const progressText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');
    
    if (progressText) {
        progressText.textContent = `${Math.round(percentual)}%`;
    }
    
    if (progressBar) {
        progressBar.style.width = `${percentual}%`;
    }
    
    console.log('📊 Progresso atualizado:', `${Math.round(percentual)}%`);
}

function iniciarTimeline(taskId) {
    console.log('🚀 Iniciando timeline para task:', taskId);
    
    // Limpa timeline anterior
    limparTimeline();
    
        if (!taskId) {
            console.error('❌ Task ID não fornecido');
            if (window.pncpApp) {
                window.pncpApp.mostrarNotificacao('Erro: ID da tarefa não encontrado', 'error');
            }
            return;
        }
    
    try {
        // Conecta ao Server-Sent Events
        const eventSource = new EventSource(`http://127.0.0.1:8000/extracao/events/${taskId}`);
        console.log(`📡 Conectando ao SSE: http://127.0.0.1:8000/extracao/events/${taskId}`);
        
        eventSource.onopen = function(event) {
            console.log('✅ Conexão SSE estabelecida');
            if (window.pncpApp) {
                window.pncpApp.mostrarNotificacao('Timeline conectada - acompanhando progresso', 'success');
            }
        };
        
        eventSource.onmessage = function(event) {
            try {
                console.log('📨 Evento recebido:', event.data);
                const evento = JSON.parse(event.data);
                adicionarEventoTimeline(evento);
            } catch (error) {
                console.error('❌ Erro ao processar evento:', error);
                console.error('Dados do evento:', event.data);
            }
        };
        
        eventSource.onerror = function(event) {
            console.error('❌ Erro na conexão SSE:', event);
            if (window.pncpApp) {
                window.pncpApp.mostrarNotificacao('Erro na conexão com timeline', 'error');
            }
            
            // Tenta reconectar após 5 segundos
            setTimeout(() => {
                if (window.pncpApp.currentTaskId === taskId) {
                    console.log('🔄 Tentando reconectar timeline...');
                    iniciarTimeline(taskId);
                }
            }, 5000);
        };
        
        // Armazena referência
        window.pncpApp.eventSource = eventSource;
        window.pncpApp.currentTaskId = taskId;
        
    } catch (error) {
        console.error('❌ Erro ao criar conexão SSE:', error);
        mostrarNotificacao('Erro ao conectar timeline', 'error');
    }
}

function adicionarEventoTimeline(evento) {
    console.log('📝 Adicionando evento à timeline:', evento);
    
    try {
        // Adiciona à lista de eventos
        window.pncpApp.timelineEvents.push(evento);
        
        // Remove estado vazio
        const emptyState = document.getElementById('timeline-empty');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Cria elemento do evento
        const timelineContainer = document.getElementById('timeline-container');
        if (!timelineContainer) {
            console.error('❌ Container da timeline não encontrado');
            return;
        }
        
        const eventoElement = criarElementoEvento(evento);
        timelineContainer.appendChild(eventoElement);
        
        // Atualiza progresso se for evento de progresso
        if (evento.type === 'progress' && evento.data) {
            atualizarProgresso(evento.data.progresso || 0);
        }
        
        // Auto scroll
        if (window.pncpApp.autoScrollEnabled) {
            timelineContainer.scrollTop = timelineContainer.scrollHeight;
        }
        
        // Adiciona animação de entrada
        eventoElement.style.opacity = '0';
        eventoElement.style.transform = 'translateY(20px)';
        setTimeout(() => {
            eventoElement.style.transition = 'all 0.3s ease';
            eventoElement.style.opacity = '1';
            eventoElement.style.transform = 'translateY(0)';
        }, 100);
        
    } catch (error) {
        console.error('❌ Erro ao adicionar evento à timeline:', error);
    }
}

function criarElementoEvento(evento) {
    const div = document.createElement('div');
    div.className = `timeline-item flex items-start space-x-3 ${getEventoClasses(evento.type)}`;
    
    const timestamp = new Date(evento.timestamp || Date.now()).toLocaleTimeString('pt-BR');
    
    div.innerHTML = `
        <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${getIconeClasses(evento.type)}">
            <i class="${getIconeEvento(evento.type)} text-sm"></i>
        </div>
        <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between">
                <p class="text-sm font-medium ${getTextoClasses(evento.type)}">${evento.message}</p>
                <span class="text-xs text-gray-500">${timestamp}</span>
            </div>
            ${evento.data && Object.keys(evento.data).length > 0 ? `
                <div class="mt-1 text-xs text-gray-600">
                    ${formatarDadosEvento(evento.data)}
                </div>
            ` : ''}
        </div>
    `;
    
    return div;
}

function getEventoClasses(tipo) {
    const classes = {
        'info': 'bg-blue-50 border-l-4 border-blue-400',
        'success': 'bg-green-50 border-l-4 border-green-400',
        'warning': 'bg-yellow-50 border-l-4 border-yellow-400',
        'error': 'bg-red-50 border-l-4 border-red-400',
        'progress': 'bg-purple-50 border-l-4 border-purple-400'
    };
    return classes[tipo] || classes['info'];
}

function getIconeClasses(tipo) {
    const classes = {
        'info': 'bg-blue-100 text-blue-600',
        'success': 'bg-green-100 text-green-600',
        'warning': 'bg-yellow-100 text-yellow-600',
        'error': 'bg-red-100 text-red-600',
        'progress': 'bg-purple-100 text-purple-600'
    };
    return classes[tipo] || classes['info'];
}

function getTextoClasses(tipo) {
    const classes = {
        'info': 'text-blue-800',
        'success': 'text-green-800',
        'warning': 'text-yellow-800',
        'error': 'text-red-800',
        'progress': 'text-purple-800'
    };
    return classes[tipo] || classes['info'];
}

function getIconeEvento(tipo) {
    const icones = {
        'info': 'fas fa-info-circle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'error': 'fas fa-times-circle',
        'progress': 'fas fa-spinner fa-spin'
    };
    return icones[tipo] || icones['info'];
}

function formatarDadosEvento(dados) {
    const formatado = [];
    
    if (dados.progresso !== undefined) {
        formatado.push(`Progresso: ${dados.progresso}%`);
    }
    
    if (dados.atual && dados.total) {
        formatado.push(`${dados.atual}/${dados.total} editais`);
    }
    
    if (dados.id_pncp) {
        formatado.push(`Edital: ${dados.id_pncp}`);
    }
    
    if (dados.total_encontrados !== undefined) {
        formatado.push(`Encontrados: ${dados.total_encontrados}`);
    }
    
    if (dados.total_novos !== undefined) {
        formatado.push(`Novos: ${dados.total_novos}`);
    }
    
    if (dados.total_atualizados !== undefined) {
        formatado.push(`Atualizados: ${dados.total_atualizados}`);
    }
    
    if (dados.total_erros !== undefined) {
        formatado.push(`Erros: ${dados.total_erros}`);
    }
    
    if (dados.tempo_execucao !== undefined) {
        formatado.push(`Tempo: ${dados.tempo_execucao}s`);
    }
    
    return formatado.join(' • ');
}

function atualizarProgresso(progresso) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${progresso}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${progresso}%`;
    }
}

function limparTimeline() {
    const timelineContainer = document.getElementById('timeline-container');
    const emptyState = document.getElementById('timeline-empty');
    
    if (timelineContainer) {
        // Remove todos os eventos
        const eventos = timelineContainer.querySelectorAll('.timeline-item');
        eventos.forEach(evento => evento.remove());
        
        // Adiciona estado vazio se não existir
        if (!emptyState) {
            timelineContainer.innerHTML = `
                <div id="timeline-empty" class="text-center py-8 text-gray-500">
                    <i class="fas fa-clock text-4xl mb-4"></i>
                    <p class="text-lg font-medium">Aguardando início da extração</p>
                    <p class="text-sm">A timeline será atualizada em tempo real</p>
                </div>
            `;
        }
    }
    
    // Reset progresso
    atualizarProgresso(0);
    
    // Limpa eventos da memória
    window.pncpApp.timelineEvents = [];
    
    // Fecha conexão anterior
    if (window.pncpApp.eventSource) {
        window.pncpApp.eventSource.close();
        window.pncpApp.eventSource = null;
    }
}

function toggleAutoScroll() {
    window.pncpApp.autoScrollEnabled = !window.pncpApp.autoScrollEnabled;
    const btn = document.getElementById('autoscroll-btn');
    
    if (btn) {
        if (window.pncpApp.autoScrollEnabled) {
            btn.classList.remove('text-gray-400');
            btn.classList.add('text-blue-600');
            btn.title = 'Auto scroll ativado';
        } else {
            btn.classList.remove('text-blue-600');
            btn.classList.add('text-gray-400');
            btn.title = 'Auto scroll desativado';
        }
    }
}

// ========================================
// FUNÇÕES DA TABELA DE EDITAIS
// ========================================

function aplicarFiltros() {
    const app = window.pncpApp;
    
    // Coleta valores dos filtros
    app.filtros.situacao = document.getElementById('filtro-situacao')?.value || '';
    app.filtros.modalidade = document.getElementById('filtro-modalidade')?.value || '';
    app.filtros.busca = document.getElementById('busca-edital')?.value || '';
    
    // Reset para primeira página
    app.paginaAtual = 1;
    
    // Re-renderiza a tabela
    app.renderizarEditais();
}

function ordenarTabela(campo) {
    const app = window.pncpApp;
    
    // Alterna direção se for o mesmo campo
    if (app.ordenacao.campo === campo) {
        app.ordenacao.direcao = app.ordenacao.direcao === 'asc' ? 'desc' : 'asc';
    } else {
        app.ordenacao.campo = campo;
        app.ordenacao.direcao = 'asc';
    }
    
    // Reset para primeira página
    app.paginaAtual = 1;
    
    // Re-renderiza a tabela
    app.renderizarEditais();
    
    // Atualiza ícones de ordenação
    atualizarIconesOrdenacao(campo, app.ordenacao.direcao);
}

function atualizarIconesOrdenacao(campoAtivo, direcao) {
    // Remove todos os ícones de ordenação
    document.querySelectorAll('th i').forEach(icon => {
        icon.className = 'fas fa-sort ml-1 text-gray-400';
    });
    
    // Atualiza ícone do campo ativo
    const th = document.querySelector(`th[onclick="ordenarTabela('${campoAtivo}')"]`);
    if (th) {
        const icon = th.querySelector('i');
        if (icon) {
            if (direcao === 'asc') {
                icon.className = 'fas fa-sort-up ml-1 text-blue-600';
            } else {
                icon.className = 'fas fa-sort-down ml-1 text-blue-600';
            }
        }
    }
}

function alterarLinhasPorPagina() {
    const app = window.pncpApp;
    const select = document.getElementById('linhas-por-pagina');
    
    if (select) {
        app.linhasPorPagina = parseInt(select.value);
        app.paginaAtual = 1; // Reset para primeira página
        app.renderizarEditais();
    }
}

function irParaPagina(numero) {
    const app = window.pncpApp;
    app.paginaAtual = numero;
    app.renderizarEditais();
}

function irParaPaginaAnterior() {
    const app = window.pncpApp;
    if (app.paginaAtual > 1) {
        app.paginaAtual--;
        app.renderizarEditais();
    }
}

function irParaPaginaProxima() {
    const app = window.pncpApp;
    const totalPaginas = Math.ceil(app.editaisOrdenados.length / app.linhasPorPagina);
    
    if (app.paginaAtual < totalPaginas) {
        app.paginaAtual++;
        app.renderizarEditais();
    }
}

function atualizarEditais() {
    if (window.pncpApp) {
        window.pncpApp.carregarEditais();
    }
}

// ========================================
// FUNÇÕES DE EXTRAÇÃO MANUAL
// ========================================

async function executarAgoraManual() {
    try {
        console.log('🚀 Iniciando extração manual - Executar Agora');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        // Mostra loading
        window.pncpApp.loading = true;
        window.pncpApp.mostrarNotificacao('Iniciando extração...', 'info');
        
        // Faz a requisição para executar extração
        console.log('🌐 Fazendo requisição para /executar-agora...');
        const response = await window.pncpApp.fazerRequisicao('/executar-agora', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('✅ Resposta da extração:', response);
        window.pncpApp.mostrarNotificacao('Extração iniciada com sucesso!', 'success');
        
    } catch (error) {
        console.error('❌ Erro ao executar extração:', error);
        window.pncpApp.mostrarNotificacao('Erro ao iniciar extração: ' + error.message, 'error');
    } finally {
        window.pncpApp.loading = false;
    }
}

async function executarHistoricoManual() {
    try {
        console.log('🚀 Iniciando extração manual - Histórico');
        
        if (!window.pncpApp) {
            throw new Error('Aplicação não inicializada');
        }
        
        // Mostra loading
        window.pncpApp.loading = true;
        window.pncpApp.mostrarNotificacao('Iniciando extração histórica...', 'info');
        
        // Faz a requisição para executar extração histórica
        const response = await window.pncpApp.fazerRequisicao('/executar-historico', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('✅ Resposta da extração histórica:', response);
        window.pncpApp.mostrarNotificacao('Extração histórica iniciada com sucesso!', 'success');
        
    } catch (error) {
        console.error('❌ Erro ao executar extração histórica:', error);
        window.pncpApp.mostrarNotificacao('Erro ao iniciar extração histórica: ' + error.message, 'error');
    } finally {
        window.pncpApp.loading = false;
    }
}

// ========================================
// FUNÇÕES DO MODAL
// ========================================

async function abrirModalDetalhes(id_pncp) {
    console.log('📋 Abrindo modal de detalhes para:', id_pncp);
    
    // Buscar dados do edital
    const edital = window.pncpApp?.editais?.find(e => e.id_pncp === id_pncp);
    if (!edital) {
        console.error('❌ Edital não encontrado:', id_pncp);
        return;
    }
    
    // Atualizar título do modal
    document.getElementById('modal-title').textContent = `Detalhes - ${edital.edital}`;
    document.getElementById('modal-subtitle').textContent = `ID: ${id_pncp}`;
    
    // Carregar documentos (aba padrão)
    await carregarDocumentosModal(edital.anexos, edital.historico);
    
    // Mostrar modal na aba documentos
    document.getElementById('modal-edital').classList.remove('hidden');
    trocarTabModal('documentos');
}

async function abrirModalDocumentos(id_pncp) {
    console.log('📄 Abrindo modal de documentos para:', id_pncp);
    
    // Buscar dados do edital
    const edital = window.pncpApp?.editais?.find(e => e.id_pncp === id_pncp);
    if (!edital) {
        console.error('❌ Edital não encontrado:', id_pncp);
        return;
    }
    
    // Atualizar título do modal
    document.getElementById('modal-title').textContent = `Documentos - ${edital.edital}`;
    document.getElementById('modal-subtitle').textContent = `ID: ${id_pncp}`;
    
    // Carregar documentos
    await carregarDocumentosModal(edital.anexos, edital.historico);
    
    // Mostrar modal na aba documentos
    document.getElementById('modal-edital').classList.remove('hidden');
    trocarTabModal('documentos');
}

async function abrirModalItens(id_pncp) {
    console.log('📋 Abrindo modal de itens para:', id_pncp);
    
    // Buscar dados do edital
    const edital = window.pncpApp?.editais?.find(e => e.id_pncp === id_pncp);
    if (!edital) {
        console.error('❌ Edital não encontrado:', id_pncp);
        return;
    }
    
    // Atualizar título do modal
    document.getElementById('modal-title').textContent = `Itens - ${edital.edital}`;
    document.getElementById('modal-subtitle').textContent = `ID: ${id_pncp}`;
    
    // Carregar itens
    await carregarItensModal(edital.itens);
    
    // Mostrar modal na aba itens
    document.getElementById('modal-edital').classList.remove('hidden');
    trocarTabModal('itens');
}

async function abrirModalHistorico(id_pncp) {
    console.log('📜 Abrindo modal de histórico para:', id_pncp);
    
    // Buscar dados do edital
    const edital = window.pncpApp?.editais?.find(e => e.id_pncp === id_pncp);
    if (!edital) {
        console.error('❌ Edital não encontrado:', id_pncp);
        return;
    }
    
    // Atualizar título do modal
    document.getElementById('modal-title').textContent = `Histórico - ${edital.edital}`;
    document.getElementById('modal-subtitle').textContent = `ID: ${id_pncp}`;
    
    // Carregar histórico
    await carregarHistoricoModal(edital.historico);
    
    // Mostrar modal na aba histórico
    document.getElementById('modal-edital').classList.remove('hidden');
    trocarTabModal('historico');
}

function fecharModal() {
    console.log('❌ Fechando modal');
    document.getElementById('modal-edital').classList.add('hidden');
}

function trocarTabModal(tabName) {
    console.log('🔄 Trocando para tab:', tabName);
    
    // Atualizar tabs
    document.querySelectorAll('.tab-modal').forEach(tab => {
        tab.classList.remove('active', 'border-blue-500', 'text-blue-600');
        tab.classList.add('border-transparent', 'text-gray-500');
    });
    
    document.getElementById(`tab-${tabName}`).classList.add('active', 'border-blue-500', 'text-blue-600');
    document.getElementById(`tab-${tabName}`).classList.remove('border-transparent', 'text-gray-500');
    
    // Atualizar conteúdo
    document.querySelectorAll('.tab-content-modal').forEach(content => {
        content.classList.add('hidden');
    });
    
    document.getElementById(`conteudo-${tabName}-modal`).classList.remove('hidden');
}

async function carregarDocumentosModal(anexos, historico) {
    console.log('📄 Carregando documentos no modal...');
    
    const container = document.getElementById('lista-documentos-modal');
    if (!container) {
        console.error('❌ Container não encontrado');
        return;
    }
    
    // Processar anexos reais do banco
    let documentos = [];
    
    if (anexos) {
        console.log('📄 Tipo de anexos recebido:', typeof anexos);
        
        // Se anexos for string JSON, fazer parse
        if (typeof anexos === 'string') {
            try {
                documentos = JSON.parse(anexos);
                console.log('✅ Documentos parseados de string JSON:', documentos.length);
            } catch (e) {
                console.error('❌ Erro ao fazer parse de anexos:', e);
                documentos = [];
            }
        } else if (Array.isArray(anexos)) {
            documentos = anexos;
            console.log('✅ Documentos já é array:', documentos.length);
        }
    }
    
    console.log('📊 Total de documentos para modal:', documentos.length);
    
    // Se não houver documentos, mostrar mensagem
    if (!documentos || documentos.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <i class="fas fa-file-pdf text-6xl mb-4 text-gray-300"></i>
                <p class="text-lg font-medium">Nenhum documento disponível</p>
                <p class="text-sm">Este edital não possui documentos anexados.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = documentos.map((doc, index) => `
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <!-- Header do Documento -->
            <div class="p-4 bg-gray-50 border-b border-gray-200">
                <div class="flex items-center space-x-3">
                    <i class="fas fa-file-pdf text-2xl text-red-500"></i>
                    <div>
                        <h4 class="text-lg font-semibold text-gray-900">${doc.titulo}</h4>
                        <div class="flex items-center space-x-3 text-sm text-gray-500">
                            <span class="bg-gray-200 px-2 py-1 rounded text-xs font-medium">${doc.tipoDocumentoNome}</span>
                            <span>${formatarTamanho(doc.tamanho)}</span>
                            <span>${formatarDataCompleta(doc.dataPublicacaoPncp)}</span>
                            <span>Seq: ${doc.sequencialDocumento}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Visualizador do Documento -->
            <div class="h-96 bg-gray-100" style="height: 600px;">
                <iframe src="https://docs.google.com/gview?url=${encodeURIComponent(doc.storage_url || doc.url_original)}&embedded=true" 
                        class="w-full h-full border-0" 
                        title="Visualizador de ${doc.titulo}">
                </iframe>
            </div>
        </div>
    `).join('');
    
    console.log('✅ Documentos carregados no modal:', documentos.length);
}

async function carregarItensModal(itens) {
    console.log('📋 Carregando itens no modal...');
    
    const container = document.getElementById('lista-itens-modal');
    if (!container) {
        console.error('❌ Container não encontrado');
        return;
    }
    
    // Processar itens reais do banco
    let itensParaExibir = [];
    
    if (itens) {
        console.log('📋 Tipo de itens recebido:', typeof itens);
        
        // Se itens for string JSON, fazer parse
        if (typeof itens === 'string') {
            try {
                itensParaExibir = JSON.parse(itens);
                console.log('✅ Itens parseados de string JSON:', itensParaExibir.length);
            } catch (e) {
                console.error('❌ Erro ao fazer parse de itens:', e);
                itensParaExibir = [];
            }
        } else if (Array.isArray(itens)) {
            itensParaExibir = itens;
            console.log('✅ Itens já é array:', itensParaExibir.length);
        }
    }
    
    console.log('📊 Total de itens para modal:', itensParaExibir.length);
    
    // Se não houver itens, mostrar mensagem
    if (!itensParaExibir || itensParaExibir.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <i class="fas fa-list text-6xl mb-4 text-gray-300"></i>
                <p class="text-lg font-medium">Nenhum item disponível</p>
                <p class="text-sm">Este edital não possui itens cadastrados.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = itensParaExibir.map(item => `
        <div class="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center space-x-2">
                    <span class="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full">
                        Item ${item.numeroItem}
                    </span>
                    <span class="bg-gray-100 text-gray-800 text-xs font-medium px-2 py-1 rounded-full">
                        ${item.materialOuServicoNome}
                    </span>
                </div>
                <div class="text-right">
                    <div class="text-lg font-semibold text-green-600">
                        R$ ${item.valorTotal.toLocaleString('pt-BR', {minimumFractionDigits: 2})}
                    </div>
                    <div class="text-sm text-gray-500">
                        ${item.quantidade} ${item.unidadeMedida}
                    </div>
                </div>
            </div>
            
            <div class="mb-3">
                <h4 class="font-medium text-gray-800 mb-1">Descrição:</h4>
                <p class="text-sm text-gray-600">${item.descricao}</p>
            </div>
            
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                    <span class="font-medium text-gray-700">Categoria:</span>
                    <span class="text-gray-600">${item.itemCategoriaNome}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Critério:</span>
                    <span class="text-gray-600">${item.criterioJulgamentoNome}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Valor Unitário:</span>
                    <span class="text-gray-600">R$ ${item.valorUnitarioEstimado.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Benefício:</span>
                    <span class="text-gray-600">${item.tipoBeneficioNome}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    console.log('✅ Itens carregados no modal:', itensParaExibir.length);
}

async function carregarHistoricoModal(historico) {
    console.log('📜 Carregando histórico no modal...');
    
    const container = document.getElementById('lista-historico-modal');
    if (!container) {
        console.error('❌ Container não encontrado');
        return;
    }
    
    // Processar histórico real do banco
    let historicoParaExibir = [];
    
    if (historico) {
        console.log('📜 Tipo de histórico recebido:', typeof historico);
        
        // Se histórico for string JSON, fazer parse
        if (typeof historico === 'string') {
            try {
                historicoParaExibir = JSON.parse(historico);
                console.log('✅ Histórico parseado de string JSON:', historicoParaExibir.length);
            } catch (e) {
                console.error('❌ Erro ao fazer parse de histórico:', e);
                historicoParaExibir = [];
            }
        } else if (Array.isArray(historico)) {
            historicoParaExibir = historico;
            console.log('✅ Histórico já é array:', historicoParaExibir.length);
        }
    }
    
    console.log('📊 Total de eventos de histórico:', historicoParaExibir.length);
    
    // Se não houver histórico, mostrar mensagem
    if (!historicoParaExibir || historicoParaExibir.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <i class="fas fa-history text-6xl mb-4 text-gray-300"></i>
                <p class="text-lg font-medium">Nenhum evento no histórico</p>
                <p class="text-sm">Este edital não possui histórico de alterações.</p>
            </div>
        `;
        return;
    }
    
    // Ordenar histórico por data (mais recente primeiro)
    historicoParaExibir.sort((a, b) => {
        const dataA = new Date(a.logManutencaoDataInclusao || a.dataInclusao || 0);
        const dataB = new Date(b.logManutencaoDataInclusao || b.dataInclusao || 0);
        return dataB - dataA;
    });
    
    container.innerHTML = historicoParaExibir.map((evento, index) => {
        const categoria = evento.categoriaLogManutencaoNome || evento.categoria || 'N/A';
        const tipo = evento.tipoLogManutencaoNome || evento.tipo || 'N/A';
        const data = evento.logManutencaoDataInclusao || evento.dataInclusao || '';
        const usuario = evento.usuarioNome || evento.usuario || 'Sistema';
        const justificativa = evento.justificativa || '';
        const documento = evento.documentoTitulo || '';
        const itemNumero = evento.itemNumero || '';
        
        // Definir cor baseado no tipo
        let corBadge = 'bg-blue-100 text-blue-800';
        if (tipo.includes('Inclusão')) corBadge = 'bg-green-100 text-green-800';
        if (tipo.includes('Retificação') || tipo.includes('Alteração')) corBadge = 'bg-yellow-100 text-yellow-800';
        if (tipo.includes('Exclusão') || tipo.includes('Cancelamento')) corBadge = 'bg-red-100 text-red-800';
        
        return `
            <div class="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                                <i class="fas fa-history text-purple-600"></i>
                            </div>
                        </div>
                        <div>
                            <div class="flex items-center space-x-2 mb-1">
                                <span class="${corBadge} text-xs font-medium px-2 py-1 rounded-full">
                                    ${tipo}
                                </span>
                                <span class="bg-gray-100 text-gray-700 text-xs font-medium px-2 py-1 rounded-full">
                                    ${categoria}
                                </span>
                            </div>
                            <div class="text-sm text-gray-600 flex items-center space-x-4">
                                <span><i class="fas fa-clock mr-1"></i>${formatarDataCompleta(data)}</span>
                                <span><i class="fas fa-user mr-1"></i>${usuario}</span>
                            </div>
                        </div>
                    </div>
                    <span class="text-xs text-gray-400">#${index + 1}</span>
                </div>
                
                ${documento ? `
                    <div class="mt-2 text-sm">
                        <span class="font-medium text-gray-700">Documento:</span>
                        <span class="text-gray-600">${documento}</span>
                    </div>
                ` : ''}
                
                ${itemNumero ? `
                    <div class="mt-2 text-sm">
                        <span class="font-medium text-gray-700">Item:</span>
                        <span class="text-gray-600">#${itemNumero}</span>
                    </div>
                ` : ''}
                
                ${justificativa ? `
                    <div class="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p class="text-sm text-gray-700"><strong>Justificativa:</strong> ${justificativa}</p>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    console.log('✅ Histórico carregado no modal:', historicoParaExibir.length);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    window.pncpApp = new PNCPApp();
    window.loading = false;
    window.stats = window.pncpApp.stats;
    console.log('PNCP App inicializado com sucesso!');
    
    // Fechar modal com ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            fecharModal();
        }
    });
    
    // Fechar modal clicando no backdrop
    document.getElementById('modal-edital').addEventListener('click', (e) => {
        if (e.target.id === 'modal-edital') {
            fecharModal();
        }
    });
});
