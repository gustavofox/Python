# Python — scripts de automação e infraestrutura

Coleção de exemplos em **Python, Node.js, Shell, Ansible e CloudFormation** para administrar recursos AWS, trabalhar com Docker e Linux e estudar programação.

Os arquivos são independentes: este repositório não é uma aplicação única e não possui um instalador ou arquivo central de dependências. Há scripts legados, trechos de referência e exemplos que precisam de correção antes de executar. As descrições abaixo refletem o código presente no repositório, inclusive quando ele difere dos comentários ou do nome do arquivo.

## Índice

- [Requisitos e formas de uso](#requisitos-e-formas-de-uso)
- [EC2, Auto Scaling e tags](#ec2-auto-scaling-e-tags)
- [Snapshots EBS](#snapshots-ebs)
- [DynamoDB](#dynamodb)
- [RDS](#rds)
- [S3 e SNS](#s3-e-sns)
- [Docker, Linux e redes](#docker-linux-e-redes)
- [Ansible](#ansible)
- [CloudFormation e políticas IAM](#cloudformation-e-políticas-iam)
- [Exercícios e material de apoio](#exercícios-e-material-de-apoio)
- [Exemplos de entradas para Lambda](#exemplos-de-entradas-para-lambda)
- [Estado da documentação](#estado-da-documentação)

## Requisitos e formas de uso

| Tipo de arquivo | Requisitos e modo de uso |
| --- | --- |
| Python com AWS | Dependência principal: `boto3`, que utiliza `botocore`. Configure credenciais, região e permissões para os recursos acessados. Alguns arquivos ainda contêm sintaxe Python 2 e precisam ser adaptados para Python 3. |
| AWS Lambda em Python | Configure o handler indicado nas tabelas e o evento esperado. Executar o arquivo com `python` não chama automaticamente o handler; alguns arquivos, porém, já fazem chamadas AWS durante a importação. |
| Node.js | `ModifyInstance.js` usa o pacote `aws-sdk` e exporta um handler Lambda. Não há `package.json` no repositório. |
| Docker | `DockerImgbackup.py` usa a interface antiga `docker.Client`, API `1.9` e socket local do Docker em Linux. Exige adaptação antes de uso em outro ambiente. |
| SSH e rede | `SSHCommand-Paramiko.py` depende de `paramiko`; o scanner depende de `scapy` e de acesso ao envio/captura de pacotes. |
| Ansible | Exige Ansible, inventário, acesso SSH aos hosts e permissões administrativas para as tarefas de instalação ou criação de usuários. |
| CloudFormation e IAM | Arquivos `.template`, alguns JSON e `vpc-stack.yml` são definições de infraestrutura; não são scripts Python. Revise os parâmetros e as referências antes de criar uma stack ou aplicar uma política. |

Antes de utilizar um exemplo, substitua IDs, ARNs, regiões, tags, hosts e caminhos pelos valores do seu ambiente. Prefira credenciais externas ao código, como um perfil AWS ou uma role de execução.

**Atenção ao efeito de cada arquivo:** há rotinas que desligam instâncias, excluem backups, criam infraestrutura, alteram regras de rede ou concedem acesso administrativo. Não execute os arquivos em lote. A revisão desta documentação não executou essas operações.

## EC2, Auto Scaling e tags

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [index.py](index.py) | Inicia **ou** para uma instância EC2 pelo ID, aguardando as transições de estado. | Handler `index.action_instance_handler`. Evento com `region`, `action` (`start` ou `stop`) e `instance_id`. O agendamento deve ser configurado separadamente; o script não cria a regra. |
| [ec2-stop-all.py](ec2-stop-all.py) | Seleciona instâncias em estado `running` e solicita a parada de todas as encontradas. | Função `lambda_handler`; não lê parâmetros do evento. Usa a região configurada no SDK e não restringe a seleção por tag. |
| [desligamentocomtag.py](desligamentocomtag.py) | Para as instâncias encontradas pelo filtro de tag `environment`. | Função `lambda_handler`. Substitua o valor `xxxxxxxx` da tag. O filtro não inclui estado da instância. |
| [PythonTagsStartMachines](PythonTagsStartMachines) | Exemplo de Lambda para iniciar instâncias paradas com a tag `Env=Dev`, em `us-east-1`. | Python sem extensão. Remova ou comente a primeira linha, `Lambda Function Start`, antes de salvar como módulo Python; a função é `lambda_handler`. |
| [PythontagsStopMachines](PythontagsStopMachines) | Exemplo de Lambda para parar instâncias em execução com a tag `Env=Dev`, em `us-east-1`. | Python sem extensão. O trecho precisa de dois-pontos e indentação corretos na função e no laço antes de executar. |
| [changeinstancetype](changeinstancetype) | Para uma EC2, aguarda o estado `stopped`, altera seu tipo para `m3.xlarge` e solicita a inicialização. | Script Python sem extensão, executado no nível principal. Configure `my_instance`, tipo de instância e região. Provoca interrupção da instância. |
| [ModifyInstance.js](ModifyInstance.js) | Faz a sequência parar → aguardar → alterar tipo → iniciar uma instância EC2, usando Promises. | Handler `ModifyInstance.handler`. Evento com `instanceId`, **`instanceRegion`** e `instanceType`. O comentário final usa `region`, mas o código lê `instanceRegion`. Não cria um agendamento. |
| [Update-autoscaling-create-launch-configuration.py](Update-autoscaling-create-launch-configuration.py) | Busca uma AMI pelas tags `CreationDate` e `ambiente`, cria uma Launch Configuration baseada em outra, atualiza o Auto Scaling Group e exclui a configuração anterior. | Função `lambda_handler`. Evento com `AutoScalingGroupName` e `LaunchConfigurationName`. Ajuste a tag de ambiente; o código usa a primeira AMI retornada e copia apenas parte das propriedades da configuração de referência. |
| [relatório-all-ec2.py](relat%C3%B3rio-all-ec2.py) | Pretende imprimir um inventário de EC2 por região, com ID, tipo, IP público, tags, VPC e subnet. | Script direto com `boto3`. As credenciais são placeholders. A comparação com `"Running"` precisa ser corrigida para `"running"`; do contrário, o relatório não lista as instâncias esperadas. A coluna chamada `Platform` imprime as tags. |
| [tag-resources](tag-resources) | Assume uma role via STS e copia tags das instâncias para seus volumes EBS. Também contém funções de associação de tags a snapshots. | Python sem extensão; função `lambda_handler`. Defina `arn`, atualmente não declarado, e a região. Só `tag_volumes()` é chamada pelo handler. As escritas de tags dos snapshots e dos volumes não utilizados estão comentadas. |

## Snapshots EBS

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [backupsnapshot.py](backupsnapshot.py) | Percorre as regiões retornadas por `describe_regions`, cria snapshots dos volumes `in-use` e copia a tag `Name` de cada volume. | Função `lambda_handler`; não lê parâmetros do evento. Usa sintaxe Python 2 e não implementa paginação nas consultas. |
| [create-snapshot-on-volume.py](create-snapshot-on-volume.py) | Executa a mesma rotina de backup de volumes em uso em múltiplas regiões presente em `backupsnapshot.py`. | Função `lambda_handler`. Apesar do nome no singular, não seleciona um volume específico. Também contém sintaxe Python 2. |
| [delete-old-snap.py](delete-old-snap.py) | Identifica snapshots de uma conta com mais de 30 dias, percorrendo múltiplas regiões. | Função `lambda_handler`; configure `account_id` e `retention_days`. **A chamada que exclui snapshots está comentada.** Expressões como `print(...) % valor` também precisam de ajuste para funcionar em Python 3. |
| [delete-snapshot-date.py](delete-snapshot-date.py) | Exclui snapshots com mais de 30 dias, preservando os criados no dia 1 de cada mês e na data fixa `2019-10-09`. | Função `lambda_handler`. Configure a conta, a região e a data de exceção. A consulta de snapshots ocorre fora do handler, na importação. Usa sintaxe Python 2 e ignora o erro `InvalidSnapshot.InUse`. |

## DynamoDB

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [dynamodb-backup.py](dynamodb-backup.py) | Solicita backup de uma tabela, envia e-mail via SES e, após sucesso dessa etapa, exclui os backups listados anteriores ao limite de retenção. Usa SNS no tratamento de falhas. | Função `lambda_handler`; evento com `TableName`. Configure remetente, destinatários e tópico SNS. **A retenção aplicada é de 1 dia**, apesar de haver uma impressão de data com 7 dias. A listagem usa limite de 100 e não pagina. |
| [backup-dynamodbok.py](backup-dynamodbok.py) | Variante que publica notificações de sucesso e falha pelo SNS e remove backups antigos da tabela. | Função `lambda_handler`; evento com `TableName`. **O limite de retenção configurado é de 5 minutos**, apesar dos comentários e impressões sobre dias. A função chamada `send_email` publica no SNS, não envia pelo SES. Também limita a listagem a 100 backups sem paginação. |

Nos dois arquivos, `current_time` é calculado na importação do módulo. Eles não aguardam a conclusão do backup antes de anunciar sucesso e iniciar a limpeza; a notificação confirma o retorno da chamada de criação, não a conclusão de todo o backup.

## RDS

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [rds-stop-start.py](rds-stop-start.py) | Lê `DBInstanceName` da configuração da função Lambda `RDSInstanceStop` e solicita a parada dessa instância RDS. | Função `lambda_handler`. Apesar do nome, **implementa apenas a parada**. Requer acesso à configuração da Lambda e ao RDS; há sintaxe Python 2. |
| [rdsfunction.py](rdsfunction.py) | Pretende iniciar ou parar bancos RDS cujos identificadores contenham algum dos textos informados em `instances`. | Função `lambda_handler`; evento com `instances` (lista) e `action` (`start` ou `stop`, em minúsculas). Corrija as aspas tipográficas e a leitura de `DBInstanceStatus` na resposta. O filtro é por substring, não por igualdade exata. |
| [rdsrestore.py](rdsrestore.py) | Seleciona o snapshot mais recente de cada banco configurado e solicita a restauração em outra instância. | Função `lambda_handler`. Configure `region`, `db_instance_class`, `db_subnet` e `instances`. O código tem sintaxe Python 2 e uma vírgula ausente na chamada de restauração; também precisa tratar a ausência de snapshots. A configuração de restauração inclui `PubliclyAccessible=True` e `MultiAZ=False`. |

## S3 e SNS

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [ListBuckets.py](ListBuckets.py) | Lista os nomes dos buckets S3 acessíveis à identidade configurada. | Script direto; usa a biblioteca **`boto`**, não `boto3`, e sintaxe Python 2. Não lista os objetos dos buckets. |
| [sns-smscel.py](sns-smscel.py) | Exemplo de envio de uma mensagem de lembrete por SMS com SNS. | Handler `sns-smscel.handler` no arquivo original; renomeie o módulo se necessário ao preparar o pacote. Configure `PhoneNumber`. O argumento `TopArn` está incorreto: a chamada precisa ser ajustada ao destino escolhido antes de executar. |

## Docker, Linux e redes

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [DockerImgbackup.py](DockerImgbackup.py) | Salva metadados de um contêiner e o conteúdo de seus volumes em um arquivo `.tar` comprimido; no modo de restauração, cria outro contêiner e recupera os volumes. | Argumentos: `backup <container>` ou `restore <backup> <novo-container>`, com caminho adicional no modo em contêiner. É código Python 2 com API Docker antiga. **Não exporta a imagem Docker**: a restauração usa a imagem referenciada nos metadados. Carrega dados com `pickle`, portanto o arquivo de backup precisa ser confiável. |
| [SSHCommand-Paramiko.py](SSHCommand-Paramiko.py) | Conecta a um host por SSH, executa `uptime` e altera o link de `/etc/localtime` para `America/Fortaleza`. | Script direto com `paramiko`. Configure host, usuário e caminho da chave privada. A alteração de fuso usa `sudo`; o código aceita automaticamente chaves de host desconhecidas. |
| [scapy.py](scapy.py) | Descobre hosts de uma sub-rede via ARP e tenta verificar portas TCP conhecidas, com opções de timeout e modo `--stealth`. | CLI com argumento `subnet`, `--timeout` e `-s`/`--stealth`. Precisa de correção: `tcp_scan()` retorna `port`, variável não definida, em vez de `dst_port`. O nome `scapy.py` também conflita com o pacote importado; renomeie o arquivo antes de usar. Destinado a redes sob sua administração. |
| [user_pass.sh](user_pass.sh) | Cria um usuário Linux, prepara `.ssh` no esqueleto de usuários, inclui o usuário no grupo `admin`, define senha e shell Bash e acrescenta uma entrada no `sudoers`. | Recebe usuário em `$1` e senha em `$2`; exige privilégios administrativos. Modifica `/etc/sudoers` diretamente, depende do grupo `admin` e não valida os argumentos. Não é uma operação idempotente. |
| [awscli-sg-lista.txt](awscli-sg-lista.txt) | Contém um comando AWS CLI para consultar um Security Group pelo ID. | Substitua o ID fixo. É uma consulta com `aws ec2 describe-security-groups`, não um template de criação. |

## Ansible

| Arquivo | O que faz | Entrada, configuração e observações |
| --- | --- | --- |
| [main.yml](main.yml) | Exemplo de provisionamento de Oracle Java 8 e WildFly/JBoss: configura repositório, instala pacotes, baixa e extrai o servidor e prepara usuário e inicialização. | Configure inventário, `hosts`, `remote_user`, privilégios e `/dados`. Faz referência a um PPA e pacotes antigos. A tarefa final repete a chave `shell`, e `remote_src` precisa ser revisado na tarefa de extração; o playbook requer correção antes de uso. |
| [ANSIBLE-PLAYBOOK-USERSLINUX-AWS.zip](ANSIBLE-PLAYBOOK-USERSLINUX-AWS.zip) | Pacote de playbook para criar usuários em hosts `webservers` e instalar suas chaves públicas em `authorized_keys`. | Extraia e revise inventário, lista de usuários e chaves. `create-users.yml` usa `sudo: yes` e `include_vars: users.yml`. O pacote também inclui arquivos de apoio descritos abaixo. |

Conteúdo do pacote Ansible:

| Caminho dentro do ZIP | Finalidade |
| --- | --- |
| `ANSIBLE-PLAYBOOK-USERSLINUX-AWS/create-users.yml` | Playbook que percorre a lista de usuários e instala suas chaves públicas. |
| `ANSIBLE-PLAYBOOK-USERSLINUX-AWS/users.yml` | Lista de nomes de usuários que serão criados. |
| `ANSIBLE-PLAYBOOK-USERSLINUX-AWS/keyfiles/authorized_keys.ria.pub` | Chave pública de exemplo consumida pelo playbook; substitua pela chave do usuário correspondente. |
| `ANSIBLE-PLAYBOOK-USERSLINUX-AWS/_config.yml` | Configuração de tema Jekyll; não participa da criação de usuários. |

## CloudFormation e políticas IAM

| Arquivo | O que define | Parâmetros e observações |
| --- | --- | --- |
| [ActionLambdaFuctionsBackup.template](ActionLambdaFuctionsBackup.template) | Role e política IAM, Lambdas de criação e exclusão de snapshots, regras agendadas e, opcionalmente, uma Lambda para iniciar/parar EC2. | Parâmetros `RetentionSnapshot`, `RegionSnapshot` e `CreateActionFunction`. Os agendamentos escritos são `cron(0 4 * * ? *)` e `cron(30 4 * * ? *)`. O código embutido usa `python2.7`; a limpeza por idade percorre snapshots da conta, e a rotina de criação também contém uma exclusão por filtros de tags `Backup` e `false`. Revise o alcance antes de adaptar. |
| [automate-alarms-ipsense.json](automate-alarms-ipsense.json) | Dois alarmes CloudWatch para uma EC2: um com ação de recuperação e outro com ação de reboot. | Parâmetro `RecoveryInstance`. Os valores configurados correspondem a 5 períodos de 60 segundos e 2 de 300 segundos, diferentes das durações escritas nas descrições. Revise também a métrica `StatusCheckFailed_Instances` e o ARN fixo da ação de reboot. |
| [cloudformationSecutiryGroup](cloudformationSecutiryGroup) | Template JSON que cria um Security Group para HTTP na porta 80, permitido a um único endereço `/32`. | Parâmetro `selectedVPCId`. O arquivo não possui extensão; revise o CIDR e os nomes antes de aplicar. |
| [securitygroupweb.json](securitygroupweb.json) | Cria um Security Group com diversas portas TCP de aplicações e monitoramento. | Parâmetro `selectedVPCId`. Há regras duplicadas, nomes de exemplo e várias liberações para `0.0.0.0/0`; ajuste portas e origens ao ambiente. |
| [main.template](main.template) | Cria uma instância EC2 web, Security Group HTTP, disco raiz de 24 GiB, volume adicional de 64 GiB, associação do volume e Elastic IP. | VPC, subnet, AMI e chave SSH estão fixadas no arquivo. O volume adicional usa `DeletionPolicy: Snapshot`. O conteúdo é YAML, apesar da extensão `.template`. |
| [VPC-PROD.template](VPC-PROD.template) | Exemplo de VPC com quatro subnets, Internet Gateway, tabela de rotas, ACL e Security Groups de acesso, web e banco de dados. | Parâmetros de cliente e zonas de disponibilidade. Há vírgula extra que invalida o JSON, placeholders de CIDR e referências de recursos inconsistentes. As quatro subnets usam a mesma tabela com rota para o Internet Gateway; os nomes não garantem separação entre rede pública e privada. |
| [vpc-stack.yml](vpc-stack.yml) | Define VPC, duas subnets públicas e duas privadas em duas zonas, Internet Gateway, um NAT Gateway com EIP, rotas e grupos de segurança para DB, APP e ELB. | Recebe CIDRs e zonas de disponibilidade. Exporta o ID da VPC e das subnets públicas. Os grupos DB/APP/ELB não declaram regras de entrada neste arquivo. |
| [IAM-user-access.template](IAM-user-access.template) | Define usuários, grupos, políticas, roles, chaves de acesso e perfil de instância para serviços e administração. | Contém nomes e referências que precisam de personalização. Alguns outputs exibem chaves de acesso e seus segredos; revise esses outputs e o escopo das permissões antes de utilizar o template. |
| [Policy-edit-SG](Policy-edit-SG) | Exemplo de política IAM para consultar recursos EC2 e autorizar ou revogar regras de entrada/saída de Security Groups. | Não é um template CloudFormation. Remova o cabeçalho textual antes de usar o bloco como JSON. A política declara `Resource: "*"`. |

## Exercícios e material de apoio

| Arquivo | Descrição | Uso e observações |
| --- | --- | --- |
| [SalaryTest.py](SalaryTest.py) | Lê um salário e calcula o valor após aumento de 5%. | Execute `python SalaryTest.py` e informe um número inteiro. O código converte a entrada com `int`, sem tratar centavos ou entradas inválidas. |
| [nota-cplus.cpp](nota-cplus.cpp) | Lê duas notas e imprime a média aritmética. | Compile com um compilador C++. A chamada `system("pause")` pressupõe um comando de ambiente Windows; o programa não classifica aprovação ou reprovação. |
| [Remoção de agente opsworks.pdf](Remo%C3%A7%C3%A3o%20de%20agente%20opsworks.pdf) | Documento de apoio intitulado “Remoção de agente opsworks”. | Material para leitura, não um script executável. |

## Exemplos de entradas para Lambda

Os objetos abaixo documentam o formato dos eventos. Eles não criam agendamentos nem corrigem os problemas indicados nas tabelas. Substitua os valores de exemplo antes de qualquer invocação.

### Iniciar ou parar EC2 — `index.py`

Handler: `index.action_instance_handler`.

```json
{
  "region": "us-east-1",
  "action": "stop",
  "instance_id": "i-SUBSTITUA_PELO_ID"
}
```

Use `"action": "start"` para solicitar a inicialização.

### Alterar o tipo de EC2 — `ModifyInstance.js`

Handler: `ModifyInstance.handler`.

```json
{
  "instanceId": "i-SUBSTITUA_PELO_ID",
  "instanceRegion": "us-east-1",
  "instanceType": "TIPO_DE_DESTINO"
}
```

### Backup DynamoDB — `dynamodb-backup.py` e `backup-dynamodbok.py`

Função: `lambda_handler`. Revise especialmente a retenção de cada variante.

```json
{
  "TableName": "NOME_DA_TABELA"
}
```

### Iniciar ou parar RDS — `rdsfunction.py`

Função: `lambda_handler`, após as correções mencionadas na tabela.

```json
{
  "instances": ["IDENTIFICADOR_DO_BANCO"],
  "action": "stop"
}
```

### Atualizar Auto Scaling — `Update-autoscaling-create-launch-configuration.py`

Função: `lambda_handler`.

```json
{
  "AutoScalingGroupName": "NOME_DO_GRUPO",
  "LaunchConfigurationName": "CONFIGURACAO_DE_REFERENCIA"
}
```

Para arquivos Python sem extensão ou com nomes pouco convenientes para importação, salve o código revisado em um módulo como `lambda_function.py` e configure `lambda_function.lambda_handler`, preservando o nome real da função quando ele for diferente.

## Estado da documentação

Este catálogo foi elaborado por leitura dos scripts, templates e arquivos de texto do pacote Ansible. A checagem de sintaxe não equivale a uma execução bem-sucedida: permissões, dependências, paginação, parâmetros e respostas dos serviços ainda precisam ser validados para cada uso. Nenhuma rotina AWS, Docker, SSH, Ansible ou de varredura de rede foi executada durante a documentação.
