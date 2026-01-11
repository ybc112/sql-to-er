// ER图编辑器核心JavaScript代码 - 标准ER图版本

// 全局变量
let svg, g, zoom;
let entities = [];
let attributes = [];
let relationships = [];
let connections = [];
let showRelationships = true; // 控制是否显示关系连线

// 切换关系显示功能
function toggleRelationships() {
    showRelationships = !showRelationships;
    const btn = document.getElementById('toggleRelationsBtn');
    
    if (showRelationships) {
        btn.innerHTML = '<i class="fas fa-link"></i> 隐藏关系连线';
        btn.className = 'btn btn-info';
    } else {
        btn.innerHTML = '<i class="fas fa-unlink"></i> 显示关系连线';
        btn.className = 'btn btn-secondary';
    }
    
    // 重新渲染图表
    renderDiagram();
}

let currentEntity = null;
let sqlEditor = null;
let width, height;
let currentEditingElement = null; // 用于内联编辑
let currentProjectId = null; // 当前项目ID
let currentProjectName = null; // 当前项目名称

// 加载和提示相关函数
function showLoading(message = '处理中...') {
    const loader = document.createElement('div');
    loader.className = 'loading-overlay';
    loader.innerHTML = `
        <div class="spinner"></div>
        <div class="loading-text">${message}</div>
    `;
    document.body.appendChild(loader);
    return loader;
}

function hideLoading(loader) {
    if (loader && loader.parentNode) {
        loader.parentNode.removeChild(loader);
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 触发动画
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 3秒后自动消失
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 默认大小设置
let defaultSizes = {
    entity: { width: 120, height: 60 },
    attribute: { rx: 60, ry: 25 },
    relationship: { width: 80, height: 50 }
};

// 文字测量相关
let textMeasureCanvas = null;
let textMeasureContext = null;

// 初始化文字测量工具
function initTextMeasurement() {
    textMeasureCanvas = document.createElement('canvas');
    textMeasureContext = textMeasureCanvas.getContext('2d');
}

// 测量文字宽度
function measureTextWidth(text, fontSize = 14, fontFamily = 'Arial, sans-serif', fontWeight = 'normal') {
    if (!textMeasureContext) {
        initTextMeasurement();
    }
    textMeasureContext.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    return textMeasureContext.measureText(text).width;
}

function getCurrentFontSizes() {
    const cs = getComputedStyle(document.documentElement);
    const parse = v => parseInt(String(v).replace('px','')) || 12;
    return {
        entity: parse(cs.getPropertyValue('--er-font-entity') || 14),
        attr: parse(cs.getPropertyValue('--er-font-attr') || 12),
        rel: parse(cs.getPropertyValue('--er-font-rel') || 12),
    };
}

// 改进的自动宽度计算，考虑更多因素
function calculateEntityWidth(name) {
    const { entity } = getCurrentFontSizes();
    const textWidth = measureTextWidth(name, entity, 'Arial, sans-serif', '600');
    const padding = 40; // 左右各20px的内边距
    const minWidth = 80; // 最小宽度
    const maxWidth = 300; // 最大宽度，避免过长
    return Math.min(maxWidth, Math.max(minWidth, textWidth + padding));
}

function calculateAttributeWidth(name) {
    const { attr } = getCurrentFontSizes();
    const textWidth = measureTextWidth(name, attr, 'Arial, sans-serif', 'normal');
    const padding = 30; // 椭圆内边距
    const minRx = 40; // 最小半径
    const maxRx = 150; // 最大半径
    return Math.min(maxRx, Math.max(minRx, (textWidth + padding) / 2));
}

function calculateRelationshipWidth(name) {
    const { rel } = getCurrentFontSizes();
    const textWidth = measureTextWidth(name, rel, 'Arial, sans-serif', 'normal');
    const padding = 30; // 菱形内边距
    const minWidth = 50; // 最小宽度
    const maxWidth = 200; // 最大宽度
    return Math.min(maxWidth, Math.max(minWidth, textWidth + padding));
}


// 初始化
function updateFontSize(value) {
    const base = parseInt(value) || 12;
    const root = document.documentElement;
    root.style.setProperty('--er-font-attr', base + 'px');
    root.style.setProperty('--er-font-rel', base + 'px');
    root.style.setProperty('--er-font-entity', (base + 2) + 'px');
    const disp = document.getElementById('font-size-value');
    if (disp) disp.textContent = String(base);
    // 重新渲染保证宽度重新测量
    renderDiagram();
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing ER editor...');
    
    // 延迟初始化，确保CSS样式已应用
    setTimeout(() => {
        initTextMeasurement();
        initCanvas();
        initSQLEditor();
        updateEntityList(); // 初始化实体列表
        
        console.log('ER editor initialization complete');
        
        // 同步一次字体大小（从滑杆读取当前值），确保初始渲染采用用户期望字号
        try {
            const initFont = document.getElementById('font-size-range')?.value || 12;
            if (typeof updateFontSize === 'function') {
                updateFontSize(initFont);
            }
        } catch (e) {
            console.warn('初始化字体大小同步失败', e);
        }
        
        // 如果有示例数据，可以在这里加载
        if (entities.length === 0) {
            console.log('No entities found, ready for import');
        }
    }, 100);
});

// 窗口大小改变时重新调整画布
window.addEventListener('resize', function() {
    if (svg) {
        const container = document.getElementById('er-canvas');
        const newWidth = container.clientWidth || container.offsetWidth || window.innerWidth - 320;
        const newHeight = container.clientHeight || container.offsetHeight || window.innerHeight - 100;
        
        if (newWidth !== width || newHeight !== height) {
            width = newWidth;
            height = newHeight;
            svg.attr('width', width).attr('height', height);
            console.log('Canvas resized to:', width, 'x', height);
        }
    }
});

// 初始化画布
function initCanvas() {
    const container = document.getElementById('er-canvas');
    
    // 确保容器有正确的尺寸，如果为0则使用默认值
    width = container.clientWidth || container.offsetWidth || 800;
    height = container.clientHeight || container.offsetHeight || 600;
    
    // 如果尺寸仍然为0，使用视窗尺寸作为后备
    if (width === 0) {
        width = window.innerWidth - 320; // 减去侧边栏宽度
    }
    if (height === 0) {
        height = window.innerHeight - 100; // 减去工具栏高度
    }
    
    console.log('Canvas dimensions:', width, 'x', height);
    
    svg = d3.select('#er-canvas')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', function(event) {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    g = svg.append('g');
    
    svg.append('defs').selectAll('marker')
        .data(['arrow'])
        .enter().append('marker')
        .attr('id', d => d)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 8)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#000');
}

// 初始化SQL编辑器
function initSQLEditor() {
    sqlEditor = ace.edit('sql-editor');
    sqlEditor.setTheme('ace/theme/monokai');
    sqlEditor.session.setMode('ace/mode/sql');
    sqlEditor.setOptions({
        fontSize: '14px',
        showPrintMargin: false,
        enableBasicAutocompletion: true,
        enableLiveAutocompletion: true
    });
}

// 标准ER图元素类
class EREntity {
    constructor(name, x, y, displayName = null) {
        this.id = 'entity_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.name = name;
        this.displayName = displayName || name;
        this.x = x;
        this.y = y;
        this.width = calculateEntityWidth(this.displayName);
        this.height = defaultSizes.entity.height;
    }

    updateName(newName) {
        this.displayName = newName;
        this.width = calculateEntityWidth(newName);
    }
}

class ERAttribute {
    constructor(name, type, entityId, isPK = false, isFK = false, displayName = null, comment = null) {
        this.id = 'attr_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.name = name;
        this.displayName = displayName || name;
        this.comment = comment;
        this.type = type;
        this.entityId = entityId;
        this.isPK = isPK;
        this.isFK = isFK;  // 新增外键标识
        this.x = 0;
        this.y = 0;
        this.rx = calculateAttributeWidth(this.displayName);
        this.ry = defaultSizes.attribute.ry;
    }

    updateName(newName) {
        this.displayName = newName;
        this.rx = calculateAttributeWidth(newName);
    }
}

class ERRelationship {
    constructor(name, fromEntityId, toEntityId, type = '1:1', displayName = null, fromAttr = null, toAttr = null) {
        this.id = 'rel_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.name = name;
        this.displayName = displayName || name;
        this.fromEntityId = fromEntityId;
        this.toEntityId = toEntityId;
        this.type = type;
        this.fromAttr = fromAttr; // 连接所用的源字段
        this.toAttr = toAttr;     // 连接所用的目标字段
        this.x = 0;
        this.y = 0;
        this.width = calculateRelationshipWidth(this.displayName);
        this.height = defaultSizes.relationship.height;
    }

    updateName(newName) {
        this.displayName = newName;
        this.width = calculateRelationshipWidth(newName);
    }
}

// 渲染标准ER图
function renderDiagram() {
    g.selectAll('*').remove();
    
    const connectionGroup = g.append('g').attr('class', 'connection-group');
    const entityGroup = g.append('g').attr('class', 'entity-group');
    const attributeGroup = g.append('g').attr('class', 'attribute-group');
    
    // 创建实体组
    const entityGroups = entityGroup.selectAll('.entity')
        .data(entities)
        .enter()
        .append('g')
        .attr('class', 'entity')
        .attr('id', d => d.id)
        .attr('transform', d => `translate(${d.x}, ${d.y})`)
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', draggedEntity)
            .on('end', dragEnded));
    
    entityGroups.append('rect')
        .attr('width', d => d.width)
        .attr('height', d => d.height)
        .attr('class', 'entity-rect')
        .attr('rx', 5);
    
    entityGroups.append('text')
        .attr('x', d => d.width / 2)
        .attr('y', d => d.height / 2)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('class', 'entity-text')
        .text(d => d.displayName)
        .style('cursor', 'pointer')
        .on('dblclick', function(event, d) {
            event.stopPropagation();
            editEntityName(d, this);
        });
    
    // 创建属性组
    const attrGroups = attributeGroup.selectAll('.attribute')
        .data(attributes)
        .enter()
        .append('g')
        .attr('class', 'attribute')
        .attr('id', d => d.id)
        .attr('transform', d => `translate(${d.x}, ${d.y})`)
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', draggedAttribute)
            .on('end', dragEnded));
    
    attrGroups.append('ellipse')
        .attr('rx', d => d.rx)
        .attr('ry', d => d.ry)
        .attr('class', 'attribute-ellipse');
    
    attrGroups.append('text')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('class', 'attribute-text')
        .text(d => d.displayName)
        .style('cursor', 'pointer')
        .on('dblclick', function(event, d) {
            event.stopPropagation();
            editAttributeName(d, this);
        });
    
    // 只有在显示关系时才创建关系组
    if (showRelationships) {
        const relationshipGroup = g.append('g').attr('class', 'relationship-group');
        
        const relGroups = relationshipGroup.selectAll('.relationship')
            .data(relationships)
            .enter()
            .append('g')
            .attr('class', 'relationship')
            .attr('id', d => d.id)
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .call(d3.drag()
                .on('start', dragStarted)
                .on('drag', draggedRelationship)
                .on('end', dragEnded));
        
        relGroups.append('polygon')
            .attr('points', d => {
                const w = d.width / 2;
                const h = d.height / 2;
                return `0,-${h} ${w},0 0,${h} -${w},0`;
            })
            .attr('class', 'relationship-diamond');
        
        relGroups.append('text')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('class', 'relationship-text')
            .text(d => d.displayName)
            .style('cursor', 'pointer')
            .on('dblclick', function(event, d) {
                event.stopPropagation();
                editRelationshipName(d, this);
            });
    }
    
    updateConnections();
}

// 更新连线
function updateConnections() {
    let connectionGroup = g.select('.connection-group');
    if (connectionGroup.empty()) {
        connectionGroup = g.insert('g', ':first-child').attr('class', 'connection-group');
    }
    
    connectionGroup.selectAll('.connection').remove();
    connectionGroup.selectAll('.connection-label-group').remove();
    
    attributes.forEach(attr => {
        const entity = entities.find(e => e.id === attr.entityId);
        if (entity) {
            const p = getEntityBorderPoint(entity, attr.x, attr.y);
            connectionGroup.append('line')
                .attr('class', 'connection entity-attr-line')
                .attr('x1', p.x)
                .attr('y1', p.y)
                .attr('x2', attr.x)
                .attr('y2', attr.y);
        }
    });
    
    // 只有在显示关系时才绘制关系连线
    if (showRelationships) {
        relationships.forEach(rel => {
            const fromEntity = entities.find(e => e.id === rel.fromEntityId);
            const toEntity = entities.find(e => e.id === rel.toEntityId);

            if (fromEntity && toEntity) {
                const fromCenterX = fromEntity.x + fromEntity.width / 2;
                const fromCenterY = fromEntity.y + fromEntity.height / 2;
                const toCenterX = toEntity.x + toEntity.width / 2;
                const toCenterY = toEntity.y + toEntity.height / 2;

                // 计算菱形的角点
                const diamondW = rel.width / 2;
                const diamondH = rel.height / 2;
                const leftPoint = { x: rel.x - diamondW, y: rel.y };
                const rightPoint = { x: rel.x + diamondW, y: rel.y };
                const topPoint = { x: rel.x, y: rel.y - diamondH };
                const bottomPoint = { x: rel.x, y: rel.y + diamondH };

                // 计算两个实体的相对位置来决定使用水平还是垂直的对称角
                const deltaX = Math.abs(fromCenterX - toCenterX);
                const deltaY = Math.abs(fromCenterY - toCenterY);

                let fromAttachPoint, toAttachPoint;

                if (deltaX > deltaY) { // 更偏水平
                    if (fromCenterX < toCenterX) {
                        fromAttachPoint = leftPoint;
                        toAttachPoint = rightPoint;
                    } else {
                        fromAttachPoint = rightPoint;
                        toAttachPoint = leftPoint;
                    }
                } else { // 更偏垂直
                    if (fromCenterY < toCenterY) {
                        fromAttachPoint = topPoint;
                        toAttachPoint = bottomPoint;
                    } else {
                        fromAttachPoint = bottomPoint;
                        toAttachPoint = topPoint;
                    }
                }

                // 从 'from' 实体边界端口到关系菱形的连线
                const fromPort = getEntityBorderPoint(fromEntity, fromAttachPoint.x, fromAttachPoint.y);
                const line1 = connectionGroup.append('line')
                    .attr('class', 'connection entity-rel-line')
                    .attr('x1', fromPort.x)
                    .attr('y1', fromPort.y)
                    .attr('x2', fromAttachPoint.x)
                    .attr('y2', fromAttachPoint.y);

                // 从关系菱形到 'to' 实体边界端口的连线 (带箭头)
                const toPort = getEntityBorderPoint(toEntity, toAttachPoint.x, toAttachPoint.y);
                const line2 = connectionGroup.append('line')
                    .attr('class', 'connection entity-rel-line')
                    .attr('x1', toAttachPoint.x)
                    .attr('y1', toAttachPoint.y)
                    .attr('x2', toPort.x)
                    .attr('y2', toPort.y)
                    .attr('marker-end', 'url(#arrow)');

                // 计算两条线的中点用于放置基数标签
                const midX1 = (fromPort.x + fromAttachPoint.x) / 2;
                const midY1 = (fromPort.y + fromAttachPoint.y) / 2;
                const midX2 = (toPort.x + toAttachPoint.x) / 2;
                const midY2 = (toPort.y + toAttachPoint.y) / 2;
                
                // 根据关系类型获取更标准的显示符号 (1, N, M)
                let typeSymbolFrom = '';
                let typeSymbolTo = '';
                switch(rel.type) {
                    case '1:1':
                        typeSymbolFrom = '1';
                        typeSymbolTo = '1';
                        break;
                    case '1:N': // fromEntity 是 'N' 端, toEntity 是 '1' 端
                        typeSymbolFrom = 'N';
                        typeSymbolTo = '1';
                        break;
                    case 'M:N':
                        typeSymbolFrom = 'M';
                        typeSymbolTo = 'N';
                        break;
                    default: // 默认为 1:N
                        typeSymbolFrom = 'N';
                        typeSymbolTo = '1';
                }
                
                const textBBox = { width: 20, height: 18 }; // 预估文本尺寸

                // 'from' 端的基数标签
                const labelGroup1 = connectionGroup.append('g')
                    .attr('class', 'connection-label-group');
                
                labelGroup1.append('rect')
                    .attr('class', 'connection-label-bg')
                    .attr('x', midX1 - textBBox.width / 2)
                    .attr('y', midY1 - textBBox.height / 2)
                    .attr('width', textBBox.width)
                    .attr('height', textBBox.height)
                    .attr('rx', 3)
                    .attr('ry', 3);
                
                labelGroup1.append('text')
                    .attr('class', 'connection-label')
                    .attr('x', midX1)
                    .attr('y', midY1)
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .text(typeSymbolFrom);
                
                // 'to' 端的基数标签
                const labelGroup2 = connectionGroup.append('g')
                    .attr('class', 'connection-label-group');
                
                labelGroup2.append('rect')
                    .attr('class', 'connection-label-bg')
                    .attr('x', midX2 - textBBox.width / 2)
                    .attr('y', midY2 - textBBox.height / 2)
                    .attr('width', textBBox.width)
                    .attr('height', textBBox.height)
                    .attr('rx', 3)
                    .attr('ry', 3);
                
                labelGroup2.append('text')
                    .attr('class', 'connection-label')
                    .attr('x', midX2)
                    .attr('y', midY2)
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .text(typeSymbolTo);
            }
        });
    }
}

// 拖拽功能
function dragStarted(event, d) {
    d3.select(this).raise().classed('dragging', true);
}

function draggedEntity(event, d) {
    const dx = event.x - d.x;
    const dy = event.y - d.y;
    d.x = event.x;
    d.y = event.y;
    d3.select(this).attr('transform', `translate(${d.x}, ${d.y})`);
    
    const entityAttrs = attributes.filter(a => a.entityId === d.id);
    entityAttrs.forEach(attr => {
        attr.x += dx;
        attr.y += dy;
        const attrElements = d3.selectAll('.attribute')
            .filter(function(attrData) { return attrData && attrData.id === attr.id; });
        if (!attrElements.empty()) {
            attrElements.attr('transform', `translate(${attr.x}, ${attr.y})`);
        }
    });
    
    updateConnections();
}

function draggedAttribute(event, d) {
    d.x = event.x;
    d.y = event.y;
    d3.select(this).attr('transform', `translate(${d.x}, ${d.y})`);
    updateConnections();
}

function draggedRelationship(event, d) {
    d.x = event.x;
    d.y = event.y;
    d3.select(this).attr('transform', `translate(${d.x}, ${d.y})`);
    updateConnections();
}

function dragEnded(event, d) {
    d3.select(this).classed('dragging', false);
}

// 内联编辑功能
function createInlineEditor(x, y, currentText, onSave, onCancel) {
    removeInlineEditor();
    showEditingHint();

    const editorContainer = document.createElement('div');
    editorContainer.className = 'inline-editor';
    editorContainer.style.position = 'absolute';
    editorContainer.style.left = x + 'px';
    editorContainer.style.top = y + 'px';
    editorContainer.style.zIndex = '1000';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentText;
    input.className = 'inline-editor-input';
    input.style.padding = '6px 10px';
    input.style.border = '2px solid #0066cc';
    input.style.borderRadius = '4px';
    input.style.fontSize = '14px';
    input.style.fontFamily = 'Arial, sans-serif';
    input.style.backgroundColor = 'white';
    input.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    input.style.outline = 'none';
    input.style.minWidth = '120px';

    const buttonContainer = document.createElement('div');
    buttonContainer.style.marginTop = '4px';
    buttonContainer.style.display = 'flex';
    buttonContainer.style.gap = '4px';

    const saveBtn = document.createElement('button');
    saveBtn.textContent = '✓';
    saveBtn.className = 'inline-editor-btn save-btn';
    saveBtn.style.padding = '2px 6px';
    saveBtn.style.border = 'none';
    saveBtn.style.borderRadius = '3px';
    saveBtn.style.backgroundColor = '#28a745';
    saveBtn.style.color = 'white';
    saveBtn.style.cursor = 'pointer';
    saveBtn.style.fontSize = '12px';

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = '✕';
    cancelBtn.className = 'inline-editor-btn cancel-btn';
    cancelBtn.style.padding = '2px 6px';
    cancelBtn.style.border = 'none';
    cancelBtn.style.borderRadius = '3px';
    cancelBtn.style.backgroundColor = '#dc3545';
    cancelBtn.style.color = 'white';
    cancelBtn.style.cursor = 'pointer';
    cancelBtn.style.fontSize = '12px';

    buttonContainer.appendChild(saveBtn);
    buttonContainer.appendChild(cancelBtn);
    editorContainer.appendChild(input);
    editorContainer.appendChild(buttonContainer);

    document.body.appendChild(editorContainer);
    currentEditingElement = editorContainer;
    input.focus();
    input.select();

    const handleSave = () => {
        const newValue = input.value.trim();
        if (newValue && newValue !== currentText) {
            onSave(newValue);
        }
        removeInlineEditor();
    };

    const handleCancel = () => {
        if (onCancel) onCancel();
        removeInlineEditor();
    };

    saveBtn.addEventListener('click', handleSave);
    cancelBtn.addEventListener('click', handleCancel);

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); handleSave(); }
        else if (e.key === 'Escape') { e.preventDefault(); handleCancel(); }
    });

    const handleClickOutside = (e) => {
        if (!editorContainer.contains(e.target)) {
            handleCancel();
            document.removeEventListener('click', handleClickOutside);
        }
    };
    setTimeout(() => { document.addEventListener('click', handleClickOutside); }, 100);

    return editorContainer;
}

function removeInlineEditor() {
    if (currentEditingElement) {
        currentEditingElement.remove();
        currentEditingElement = null;
    }
}

function showEditingHint() {
    const existingHint = document.querySelector('.editing-hint');
    if (existingHint) {
        existingHint.remove();
    }
    const hint = document.createElement('div');
    hint.className = 'editing-hint';
    hint.textContent = '按 Enter 保存，按 Esc 取消';
    document.body.appendChild(hint);
    setTimeout(() => { if (hint.parentNode) { hint.remove(); } }, 3000);
}

function editEntityName(entityData, textElement) {
    const rect = textElement.getBoundingClientRect();
    const x = rect.left + window.scrollX - 60;
    const y = rect.top + window.scrollY - 40;

    createInlineEditor(x, y, entityData.displayName, (newName) => {
        entityData.updateName(newName);
        d3.select(textElement).text(entityData.displayName);
        const entityGroup = d3.select(textElement.parentNode);
        entityGroup.select('.entity-rect').attr('width', entityData.width);
        d3.select(textElement).attr('x', entityData.width / 2);
        updateConnections();
        updateEntityList();
    });
}

function editAttributeName(attributeData, textElement) {
    const rect = textElement.getBoundingClientRect();
    const x = rect.left + window.scrollX - 60;
    const y = rect.top + window.scrollY - 40;

    createInlineEditor(x, y, attributeData.displayName, (newValue) => {
        attributeData.updateName(newValue);
        d3.select(textElement).text(newValue);
        const attrGroup = d3.select(textElement.parentNode);
        attrGroup.select('.attribute-ellipse').attr('rx', attributeData.rx);
        updateConnections();
    });
}

function editRelationshipName(relationshipData, textElement) {
    const rect = textElement.getBoundingClientRect();
    const x = rect.left + window.scrollX - 60;
    const y = rect.top + window.scrollY - 40;

    createInlineEditor(x, y, relationshipData.displayName, (newName) => {
        relationshipData.updateName(newName);
        d3.select(textElement).text(relationshipData.displayName);
        const relGroup = d3.select(textElement.parentNode);
        const w = relationshipData.width / 2;
        const h = relationshipData.height / 2;
        relGroup.select('polygon').attr('points', `0,-${h} ${w},0 0,${h} -${w},0`);
        updateConnections();
    });
}

/**
 * 基于属性数量与尺寸估算属性环半径（供布局尺寸估算使用）
 * 与 arrangeAttributes 半径策略一致，但不做邻近实体避让，仅用于 dagre 节点尺寸估算
 */
function estimateAttributeRadii(entity, entityAttrs) {
    if (!entity || !entityAttrs || entityAttrs.length === 0) {
        return { radiusX: 0, radiusY: 0, maxRx: 0, maxRy: 0 };
    }
    let baseRadiusX = Math.max(entity.width / 2 + 50, 80);
    let baseRadiusY = Math.max(entity.height / 2 + 40, 70);

    const maxRx = Math.max(...entityAttrs.map(a => a.rx), 30);
    const maxRy = Math.max(...entityAttrs.map(a => a.ry), 20);

    const attrPerimeter = entityAttrs.reduce((sum, a) => sum + (a.rx * 2) + 20, 0);
    const requiredCircumference = Math.max(attrPerimeter, 2 * Math.PI * 80);
    const radiusMultiplier = Math.max(1, requiredCircumference / (2 * Math.PI * 80));

    baseRadiusX = baseRadiusX * Math.min(radiusMultiplier, 1.5) + 30;
    baseRadiusY = baseRadiusY * Math.min(radiusMultiplier, 1.5) + 25;

    return { radiusX: baseRadiusX, radiusY: baseRadiusY, maxRx, maxRy };
}

/**
 * 计算从实体中心指向目标点时，与实体矩形边界的交点（端口点）
 */
function getEntityBorderPoint(entity, targetX, targetY) {
    const cx = entity.x + entity.width / 2;
    const cy = entity.y + entity.height / 2;
    const dx = targetX - cx;
    const dy = targetY - cy;
    if (dx === 0 && dy === 0) return { x: cx, y: cy };
    const halfW = entity.width / 2;
    const halfH = entity.height / 2;
    const scale = Math.max(Math.abs(dx) / halfW, Math.abs(dy) / halfH);
    return { x: cx + dx / scale, y: cy + dy / scale };
}

// 自动排列属性 (V4 - 紧凑优化版)
function arrangeAttributes(entityId) {
    const entity = entities.find(e => e.id === entityId);
    if (!entity) return;

    const entityAttrs = attributes.filter(a => a.entityId === entityId);
    if (entityAttrs.length === 0) return;

    // 大幅减少基础半径，让属性更靠近实体
    let baseRadiusX = Math.max(entity.width / 2 + 50, 80); // 减少到50px（原80px）
    let baseRadiusY = Math.max(entity.height / 2 + 40, 70); // 减少到40px（原60px）
    
    // 根据属性数量调整，但保持较小的半径
    const maxAttrWidth = Math.max(...entityAttrs.map(attr => attr.rx * 2), 60);
    const attrPerimeter = entityAttrs.reduce((sum, attr) => sum + (attr.rx * 2) + 20, 0); // 减少间隔
    const requiredCircumference = Math.max(attrPerimeter, 2 * Math.PI * 80); // 减少基础周长
    const radiusMultiplier = Math.max(1, requiredCircumference / (2 * Math.PI * 80));
    
    // 应用更紧凑的半径
    baseRadiusX = baseRadiusX * Math.min(radiusMultiplier, 1.5) + 30; // 限制最大倍数并减少额外间距
    baseRadiusY = baseRadiusY * Math.min(radiusMultiplier, 1.5) + 25;
    
    // 简化重叠检查，只做基本的避让
    const otherEntities = entities.filter(e => e.id !== entityId);
    let finalRadiusX = baseRadiusX;
    let finalRadiusY = baseRadiusY;
    
    // 只对很近的实体做避让
    for (const otherEntity of otherEntities) {
        const distanceX = Math.abs(entity.x + entity.width/2 - otherEntity.x - otherEntity.width/2);
        const distanceY = Math.abs(entity.y + entity.height/2 - otherEntity.y - otherEntity.height/2);
        
        // 只有距离很近时才调整
        if (distanceX < 200 && distanceY < 200) {
            const minRequiredX = distanceX / 3 + otherEntity.width / 2 + 20; // 减少避让距离
            const minRequiredY = distanceY / 3 + otherEntity.height / 2 + 20;
            
            if (finalRadiusX < minRequiredX) finalRadiusX = Math.min(minRequiredX, baseRadiusX * 1.3);
            if (finalRadiusY < minRequiredY) finalRadiusY = Math.min(minRequiredY, baseRadiusY * 1.3);
        }
    }
    
    const angleStep = (2 * Math.PI) / entityAttrs.length;
    let startAngle = -Math.PI / 2; // 从顶部开始
    
    // 特殊情况的角度优化
    if (entityAttrs.length === 2) {
        startAngle = -Math.PI / 3; // 两个属性分布更均匀
    } else if (entityAttrs.length === 3) {
        startAngle = -Math.PI / 2; // 三个属性从顶部开始
    }

    entityAttrs.forEach((attr, i) => {
        const angle = startAngle + i * angleStep;
        attr.x = entity.x + entity.width / 2 + Math.cos(angle) * finalRadiusX;
        attr.y = entity.y + entity.height / 2 + Math.sin(angle) * finalRadiusY;
    });
}

// 导入SQL
function importSQL() {
    const exampleSQL = `-- 输入您的SQL语句
-- 系统会自动解析并生成标准ER图

CREATE TABLE Department (
    dept_id INT PRIMARY KEY,
    dept_name VARCHAR(50) NOT NULL,
    location VARCHAR(100)
);

CREATE TABLE Employee (
    emp_id INT PRIMARY KEY,
    emp_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    hire_date DATE,
    salary DECIMAL(10, 2),
    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id)
);

CREATE TABLE Project (
    project_id INT PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(12, 2)
);

CREATE TABLE Employee_Project (
    emp_id INT,
    project_id INT,
    role VARCHAR(50),
    hours_worked INT,
    PRIMARY KEY (emp_id, project_id),
    FOREIGN KEY (emp_id) REFERENCES Employee(emp_id),
    FOREIGN KEY (project_id) REFERENCES Project(project_id)
);`;
    
    sqlEditor.setValue(exampleSQL);
    sqlEditor.clearSelection();
    
    document.getElementById('sql-modal-title').textContent = '导入SQL - 生成标准ER图';
    document.getElementById('sql-action-btn').textContent = '解析并生成ER图';
    document.getElementById('sql-action-btn').onclick = executeImport;
    showModal('sql-modal');
}

// 全局变量用于存储待执行的导入操作
let pendingImportData = null;

// 显示扣费确认弹窗
function showChargeConfirmModal(cost, balance) {
    document.getElementById('charge-cost').textContent = `¥${cost.toFixed(2)}`;
    document.getElementById('charge-balance').textContent = `¥${balance.toFixed(2)}`;
    document.getElementById('charge-after').textContent = `¥${(balance - cost).toFixed(2)}`;
    
    // 使用新的显示方式
    const modal = document.getElementById('charge-confirm-modal');
    modal.classList.add('show');
    modal.style.display = 'flex';
}

// 关闭扣费确认弹窗
function closeChargeConfirm() {
    const modal = document.getElementById('charge-confirm-modal');
    modal.classList.remove('show');
    modal.style.display = 'none';
    pendingImportData = null;
}

// 确认扣费并执行导入
async function confirmCharge() {
    // 先关闭弹窗
    const modal = document.getElementById('charge-confirm-modal');
    modal.classList.remove('show');
    modal.style.display = 'none';
    
    // 执行导入
    if (pendingImportData) {
        const data = pendingImportData;
        pendingImportData = null;
        await doImport(data.sql, data.enableTranslation);
    }
}

async function executeImport() {
    const sql = sqlEditor.getValue();
    if (!sql.trim()) {
        showToast('请输入SQL语句', 'warning');
        return;
    }

    // 获取翻译选项
    const enableTranslation = document.getElementById('enable-translation').checked;

    // 如果启用了AI翻译，先获取价格并弹窗确认
    if (enableTranslation) {
        try {
            // 获取翻译价格信息
            const priceResponse = await fetch('/api/get_translation_price');
            const priceData = await priceResponse.json();
            
            if (!priceData.success) {
                showToast('获取价格信息失败', 'error');
                return;
            }
            
            // 检查是否登录
            if (!priceData.logged_in) {
                showToast('AI翻译功能需要登录后使用', 'warning');
                if (confirm('是否跳转到登录页面？')) {
                    window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
                }
                return;
            }
            
            // 检查余额是否充足
            if (!priceData.sufficient) {
                showToast(`余额不足！AI翻译需要 ${priceData.cost.toFixed(2)} 元，当前余额 ${priceData.balance.toFixed(2)} 元`, 'warning');
                if (confirm('是否跳转到充值页面？')) {
                    window.location.href = '/profile#recharge';
                }
                return;
            }
            
            // 保存待执行数据，显示美观的确认弹窗
            pendingImportData = { sql, enableTranslation };
            showChargeConfirmModal(priceData.cost, priceData.balance);
            return; // 等待用户确认
            
        } catch (error) {
            showToast('获取价格信息失败: ' + error.message, 'error');
            return;
        }
    }

    // 不需要翻译时直接执行
    await doImport(sql, enableTranslation);
}

// 实际执行导入操作
async function doImport(sql, enableTranslation) {
    const loader = showLoading(enableTranslation ? '正在解析SQL并智能翻译...' : '正在解析SQL...');

    try {
        const response = await fetch('/api/parse_sql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sql: sql,
                enableTranslation: enableTranslation
            })
        });

        const data = await response.json();
        if (!response.ok) {
            // 处理特殊错误情况
            if (data.need_login) {
                showToast('AI翻译功能需要登录后使用，请先登录', 'warning');
                if (confirm('是否跳转到登录页面？')) {
                    window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
                }
                return;
            }
            if (data.need_recharge) {
                showToast(`余额不足！AI翻译需要 ${data.cost?.toFixed(2) || '2.00'} 元，当前余额 ${data.balance?.toFixed(2) || '0.00'} 元`, 'warning');
                if (confirm('是否跳转到充值页面？')) {
                    window.location.href = '/profile#recharge';
                }
                return;
            }
            throw new Error(data.error || '解析失败');
        }
        
        entities = [];
        attributes = [];
        relationships = [];
        
        data.entities.forEach((entityData, index) => {
            const entity = new EREntity(
                entityData.name,
                200 + (index % 3) * 300,
                100 + Math.floor(index / 3) * 300,
                entityData.displayName
            );
            entities.push(entity);
            
            entityData.attributes.forEach((attrData) => {
                const attr = new ERAttribute(
                    attrData.name, attrData.type, entity.id, attrData.isPK, attrData.isFK,
                    attrData.displayName, attrData.comment
                );
                attributes.push(attr);
            });
            arrangeAttributes(entity.id);
        });
        
        data.relationships.forEach((relData) => {
            const fromEntity = entities.find(e => e.name === relData.from);
            const toEntity = entities.find(e => e.name === relData.to);
            if (fromEntity && toEntity) {
                const rel = new ERRelationship(
                    relData.name,
                    fromEntity.id,
                    toEntity.id,
                    relData.type || '1:N',
                    relData.displayName,
                    relData.fromAttr,
                    relData.toAttr
                );
                rel.x = (fromEntity.x + toEntity.x) / 2 + fromEntity.width / 2;
                rel.y = (fromEntity.y + toEntity.y) / 2 + fromEntity.height / 2;
                relationships.push(rel);
            }
        });
        
        closeModal('sql-modal');
        updateEntityList();

        // 导入成功后立即执行自动布局，提供更好的用户体验
        setTimeout(() => {
            autoLayout();

            // 构建成功提示消息
            let successMessage = `成功导入 ${entities.length} 个实体，${relationships.length} 个关系`;
            if (enableTranslation) {
                if (data.translationApplied) {
                    if (data.translationCharged) {
                        successMessage += ' (已应用AI智能翻译，已扣费)';
                    } else {
                        successMessage += ' (已应用AI智能翻译)';
                    }
                } else {
                    successMessage += ' (翻译失败，使用原始名称，未扣费)';
                }
            }

            showToast(successMessage, 'success');
        }, 50); // 短暂延迟确保UI更新
        
    } catch (error) {
        showToast('导入失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

// 自动布局 - V5 紧凑优化版
function autoLayout() {
    if (entities.length === 0) {
        console.warn('没有实体可进行布局');
        return;
    }

    // 检查dagre库是否可用
    if (typeof dagre === 'undefined' || !dagre.graphlib) {
        console.error('Dagre布局库未正确加载');
        alert('布局功能暂时不可用：依赖库加载失败。请刷新页面重试。');
        return;
    }

    try {
        console.log(`开始自动布局，共 ${entities.length} 个实体`);
        
        // 创建新的有向图
        const g_layout = new dagre.graphlib.Graph();
        
        // 设置图的全局属性 - 优化间距参数
        g_layout.setGraph({
            rankdir: 'TB',        // 从上到下布局
            nodesep: 150,         // 节点间距减少到150px（原250px）
            ranksep: 200,         // 层级间距减少到200px（原350px）
            marginx: 60,          // 左右边距减少到60px（原100px）
            marginy: 60,          // 上下边距减少到60px（原100px）
            edgesep: 30,          // 边的间距减少（原50px）
            rankmargin: 50        // 层级边距减少（原80px）
        });
        
        // 设置默认边标签
        g_layout.setDefaultEdgeLabel(() => ({}));

        // 添加节点到图中，使用与属性环一致的尺寸估算，保证布局与渲染一致
        entities.forEach(entity => {
            const entityAttrs = attributes.filter(a => a.entityId === entity.id);
            let effectiveWidth = entity.width;
            let effectiveHeight = entity.height;

            if (entityAttrs.length > 0) {
                const { radiusX, radiusY, maxRx, maxRy } = estimateAttributeRadii(entity, entityAttrs);
                // 属性环中心半径 + 椭圆自身半径，得到整体半宽/半高
                const totalHalfW = Math.max(entity.width / 2, radiusX + maxRx);
                const totalHalfH = Math.max(entity.height / 2, radiusY + maxRy);
                effectiveWidth = totalHalfW * 2;
                effectiveHeight = totalHalfH * 2;
            }

            g_layout.setNode(entity.id, { 
                label: entity.displayName, 
                width: effectiveWidth, 
                height: effectiveHeight 
            });
        });

        // 添加边到图中（基于关系）
        relationships.forEach(rel => {
            g_layout.setEdge(rel.fromEntityId, rel.toEntityId, {
                label: rel.displayName || '',
                weight: 1
            });
        });

        console.log(`图构建完成，开始执行布局算法...`);
        
        // 执行布局算法
        dagre.layout(g_layout);
        
        console.log(`布局算法执行完成，开始应用位置...`);

        // 应用计算出的位置到实体
        let appliedCount = 0;
        g_layout.nodes().forEach(nodeId => {
            const node = g_layout.node(nodeId);
            if (node) {
                const entity = entities.find(e => e.id === nodeId);
                if (entity) {
                    // 将实体置于计算位置的中心
                    entity.x = node.x - entity.width / 2;
                    entity.y = node.y - entity.height / 2;
                    appliedCount++;
                }
            }
        });
        
        console.log(`已应用 ${appliedCount} 个实体的位置`);
        
        // 重新排列所有实体的属性
        entities.forEach(entity => {
            arrangeAttributes(entity.id);
        });

        // 优化关系位置 - 减少偏移量
        relationships.forEach(rel => {
            const fromEntity = entities.find(e => e.id === rel.fromEntityId);
            const toEntity = entities.find(e => e.id === rel.toEntityId);
            
            if (fromEntity && toEntity) {
                // 计算两个实体中心点
                const fromCenterX = fromEntity.x + fromEntity.width / 2;
                const fromCenterY = fromEntity.y + fromEntity.height / 2;
                const toCenterX = toEntity.x + toEntity.width / 2;
                const toCenterY = toEntity.y + toEntity.height / 2;
                
                // 关系菱形放在连线的中点
                rel.x = (fromCenterX + toCenterX) / 2;
                rel.y = (fromCenterY + toCenterY) / 2;
                
                // 减少偏移量
                if (Math.abs(fromCenterX - toCenterX) < 30) {
                    rel.x += 25; // 减少向右偏移（原40px）
                }
                if (Math.abs(fromCenterY - toCenterY) < 30) {
                    rel.y += 20; // 减少向下偏移（原30px）
                }
            }
        });

        console.log(`布局完成，开始重新渲染...`);
        
        // 重新渲染图表
        renderDiagram();
        
        // 延迟执行缩放适应，确保渲染完成
    setTimeout(() => {
            zoomFit();
            console.log(`紧凑布局完成！`);
        }, 100);
        
    } catch (error) {
        console.error('自动布局过程中发生错误:', error);
        alert(`自动布局失败: ${error.message}\n\n请检查控制台获取详细信息，或尝试手动调整布局。`);
    }
}

// --- 辅助功能函数 ---

/**
 * 清空图表
 */
function clearDiagram() {
    if (confirm('确定要清空当前图表吗？此操作不可撤销。')) {
        entities = [];
        attributes = [];
        relationships = [];
        connections = [];
        
        // 清空SQL编辑器
        if (sqlEditor) {
            sqlEditor.setValue('-- 已清空\n-- 请输入新的SQL语句或导入示例');
            sqlEditor.clearSelection();
        }
        
        renderDiagram();
        updateEntityList();
        
        console.log('图表已清空');
    }
}

/**
 * 加载示例数据
 */
function loadExample() {
    const exampleSQL = `-- 图书管理系统示例
-- 这是一个完整的图书管理系统数据库设计

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active'
);

CREATE TABLE books (
    book_id INT PRIMARY KEY AUTO_INCREMENT,
    isbn VARCHAR(17) UNIQUE,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100) NOT NULL,
    publisher VARCHAR(100),
    publication_year YEAR,
    category VARCHAR(50),
    language VARCHAR(30) DEFAULT 'Chinese',
    pages INT,
    price DECIMAL(8, 2),
    stock_quantity INT DEFAULT 0,
    available_quantity INT DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    admin_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role ENUM('super_admin', 'admin', 'librarian') DEFAULT 'librarian',
    permissions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE borrow_records (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    borrow_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    fine_amount DECIMAL(6, 2) DEFAULT 0.00,
    status ENUM('borrowed', 'returned', 'overdue', 'lost') DEFAULT 'borrowed',
    notes TEXT,
    processed_by INT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (processed_by) REFERENCES admins(admin_id) ON DELETE SET NULL
);`;

    if (sqlEditor) {
        sqlEditor.setValue(exampleSQL);
        sqlEditor.clearSelection();
    }
    
    console.log('已加载示例SQL');
}

/**
 * 缩放控制函数
 */
function zoomIn() {
    if (svg && zoom) {
        svg.transition().duration(300).call(zoom.scaleBy, 1.2);
    }
}

function zoomOut() {
    if (svg && zoom) {
        svg.transition().duration(300).call(zoom.scaleBy, 0.8);
    }
}

function zoomReset() {
    if (svg && zoom) {
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    }
}

/**
 * 显示导出图片模态框
 */
function showExportImageModal() {
    // 检查是否有ER图
    if (entities.length === 0) {
        alert('请先导入SQL或创建ER图');
        return;
    }
    showModal('export-image-modal');
}

/**
 * 根据选项导出图片
 */
function exportImageWithOptions() {
    const format = document.querySelector('input[name="export-image-format"]:checked').value;
    const withBackground = document.getElementById('export-with-background').checked;
    const currentViewOnly = document.getElementById('export-current-view').checked;
    const filename = document.getElementById('export-filename').value || 'er-diagram';
    
    closeModal('export-image-modal');
    
    switch(format) {
        case 'png':
            exportAsPNG(filename, withBackground, currentViewOnly);
            break;
        case 'svg':
            exportAsSVG(filename, withBackground, currentViewOnly);
            break;
    }
}

/**
 * 导出为PNG图片
 */
function exportAsPNG(filename, withBackground, currentViewOnly) {
    try {
        const svgElement = document.querySelector('#er-canvas svg');
        if (!svgElement) {
            alert('没有找到图表内容');
            return;
        }

        // 确保DOM与最新数据同步 - 重新渲染一次
        renderDiagram();
        
        // 获取导出区域
        let exportBounds;
        if (currentViewOnly) {
            // 当前视图区域
            const transform = d3.zoomTransform(svgElement);
            exportBounds = {
                x: -transform.x / transform.k,
                y: -transform.y / transform.k,
                width: width / transform.k,
                height: height / transform.k
            };
        } else {
            // 计算所有元素的真实边界
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            let hasElements = false;
            
            // 遍历所有实体
            entities.forEach(entity => {
                minX = Math.min(minX, entity.x);
                minY = Math.min(minY, entity.y);
                maxX = Math.max(maxX, entity.x + entity.width);
                maxY = Math.max(maxY, entity.y + entity.height);
                hasElements = true;
            });
            
            // 遍历所有属性
            attributes.forEach(attr => {
                minX = Math.min(minX, attr.x - attr.rx);
                minY = Math.min(minY, attr.y - attr.ry);
                maxX = Math.max(maxX, attr.x + attr.rx);
                maxY = Math.max(maxY, attr.y + attr.ry);
                hasElements = true;
            });
            
            // 遍历所有关系
            relationships.forEach(rel => {
                minX = Math.min(minX, rel.x - rel.width / 2);
                minY = Math.min(minY, rel.y - rel.height / 2);
                maxX = Math.max(maxX, rel.x + rel.width / 2);
                maxY = Math.max(maxY, rel.y + rel.height / 2);
                hasElements = true;
            });
            
            // 处理连接线的边界（考虑连接线可能超出元素边界）
            relationships.forEach(rel => {
                const fromEntity = entities.find(e => e.id === rel.fromEntityId);
                const toEntity = entities.find(e => e.id === rel.toEntityId);
                if (fromEntity && toEntity) {
                    // 考虑连接线的起点和终点
                    minX = Math.min(minX, fromEntity.x + fromEntity.width / 2, toEntity.x + toEntity.width / 2);
                    minY = Math.min(minY, fromEntity.y + fromEntity.height / 2, toEntity.y + toEntity.height / 2);
                    maxX = Math.max(maxX, fromEntity.x + fromEntity.width / 2, toEntity.x + toEntity.width / 2);
                    maxY = Math.max(maxY, fromEntity.y + fromEntity.height / 2, toEntity.y + toEntity.height / 2);
                }
            });
            
            // 如果没有元素，使用默认范围
            if (!hasElements || !isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) {
                // 尝试使用 g 元素的边界框作为后备
                const gElement = g.node();
                const bbox = gElement.getBBox();
                if (bbox.width > 0 && bbox.height > 0) {
                    minX = bbox.x;
                    minY = bbox.y;
                    maxX = bbox.x + bbox.width;
                    maxY = bbox.y + bbox.height;
                } else {
                    minX = 0;
                    minY = 0;
                    maxX = width;
                    maxY = height;
                }
            }
            
            // 添加边距
            const padding = 50;
            exportBounds = {
                x: minX - padding,
                y: minY - padding,
                width: (maxX - minX) + padding * 2,
                height: (maxY - minY) + padding * 2
            };
            
            // 确保最小尺寸
            exportBounds.width = Math.max(exportBounds.width, 400);
            exportBounds.height = Math.max(exportBounds.height, 300);
        }
        
        console.log('Export bounds:', exportBounds); // 调试信息
        console.log('Entities:', entities.length, 'Attributes:', attributes.length, 'Relationships:', relationships.length); // 调试信息
        
        // 创建一个新的SVG用于导出
        const exportSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        exportSvg.setAttribute('width', exportBounds.width);
        exportSvg.setAttribute('height', exportBounds.height);
        exportSvg.setAttribute('viewBox', `${exportBounds.x} ${exportBounds.y} ${exportBounds.width} ${exportBounds.height}`);
        exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        exportSvg.setAttribute('style', 'background-color: ' + (withBackground ? 'white' : 'transparent'));
        
        // 添加完整的样式（使用当前CSS变量计算后的字号，避免硬编码）
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        const { entity: __fontEntity, attr: __fontAttr, rel: __fontRel } = getCurrentFontSizes();
        style.textContent = `
            .entity-rect { fill: white; stroke: black; stroke-width: 2; }
            .entity-text { font-family: Arial, sans-serif; font-size: ${__fontEntity}px; font-weight: 600; fill: black; }
            .attribute-ellipse { fill: white; stroke: black; stroke-width: 1.5; }
            .attribute-text { font-family: Arial, sans-serif; font-size: ${__fontAttr}px; fill: black; }
            .relationship polygon { fill: white; stroke: black; stroke-width: 2; }
            .relationship-text { font-family: Arial, sans-serif; font-size: ${__fontRel}px; font-style: italic; fill: black; }
            .connection { stroke: black; stroke-width: 1.5; fill: none; }
            .connection-label-bg { fill: white; stroke: black; stroke-width: 1; }
            .connection-label { font-size: ${__fontRel}px; font-weight: bold; fill: black; }
            text { fill: black; }
            .entity-attr-line { stroke: black; stroke-width: 1.5; }
            .entity-rel-line { stroke: black; stroke-width: 1.5; }
        `;
        exportSvg.appendChild(style);
        
        // 克隆定义（markers等）
        const defs = svgElement.querySelector('defs');
        if (defs) {
            exportSvg.appendChild(defs.cloneNode(true));
        }
        
        // 添加背景
        if (withBackground) {
            const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            background.setAttribute('x', exportBounds.x);
            background.setAttribute('y', exportBounds.y);
            background.setAttribute('width', exportBounds.width);
            background.setAttribute('height', exportBounds.height);
            background.setAttribute('fill', 'white');
            exportSvg.appendChild(background);
        }
        
        // 克隆g元素及其所有内容
        const gClone = g.node().cloneNode(true);
        // 确保g元素没有transform属性，因为我们已经在viewBox中处理了定位
        gClone.removeAttribute('transform');

        // 将当前字号内联到文本节点，避免样式层叠差异导致导出与显示不一致
        (function __inlineFontForPNG() {
            const { entity: __fontEntity, attr: __fontAttr, rel: __fontRel } = getCurrentFontSizes();
            const texts = gClone.querySelectorAll('text');
            texts.forEach(t => {
                const cls = t.getAttribute('class') || '';
                let size = __fontAttr;
                let weight = 'normal';
                if (cls.includes('entity-text')) { size = __fontEntity; weight = '600'; }
                else if (cls.includes('relationship-text')) { size = __fontRel; }
                else if (cls.includes('connection-label')) { size = __fontRel; weight = 'bold'; }
                // 直接写入行内样式，确保序列化后仍然生效
                t.setAttribute('font-family', 'Arial, sans-serif');
                t.setAttribute('font-size', String(size));
                if (weight) t.setAttribute('font-weight', weight);
                // 清除可能残留的样式属性冲突
                const styleAttr = t.getAttribute('style') || '';
                // 去除旧的 font-size 片段，重新写入
                const cleaned = styleAttr.replace(/font-size\s*:\s*[^;]+;?/gi, '').replace(/font-weight\s*:\s*[^;]+;?/gi, '');
                t.setAttribute('style', (cleaned + `;font-size:${size}px;${weight ? `font-weight:${weight};` : ''}`).replace(/^;/, ''));
            });
        })();

        exportSvg.appendChild(gClone);

        // 转换为图片
        const svgData = new XMLSerializer().serializeToString(exportSvg);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        // 设置高质量导出
        const scale = 2; // 2x 分辨率
        canvas.width = exportBounds.width * scale;
        canvas.height = exportBounds.height * scale;
        ctx.scale(scale, scale);
        
        img.onload = function() {
            if (withBackground) {
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, exportBounds.width, exportBounds.height);
            }
            ctx.drawImage(img, 0, 0, exportBounds.width, exportBounds.height);
            
            // 下载图片
            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.download = filename + '.png';
                a.href = url;
                a.click();
                URL.revokeObjectURL(url);
                showToast('图片导出成功！', 'success');
            }, 'image/png', 1.0);
        };
        
        img.onerror = function() {
            console.error('SVG转换失败');
            alert('导出失败，请尝试使用SVG格式或服务器生成');
        };
        
        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
        
    } catch (error) {
        console.error('导出图片失败:', error);
        alert('导出图片失败，请稍后重试');
    }
}

/**
 * 导出为SVG矢量图
 */
function exportAsSVG(filename, withBackground, currentViewOnly) {
    try {
        const svgElement = document.querySelector('#er-canvas svg');
        if (!svgElement) {
            alert('没有找到图表内容');
            return;
        }

        // 确保DOM与最新数据同步 - 重新渲染一次
        renderDiagram();
        
        // 获取导出区域 - 使用与PNG导出完全相同的逻辑
        let exportBounds;
        if (currentViewOnly) {
            const transform = d3.zoomTransform(svgElement);
            exportBounds = {
                x: -transform.x / transform.k,
                y: -transform.y / transform.k,
                width: width / transform.k,
                height: height / transform.k
            };
        } else {
            // 计算所有元素的真实边界
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            let hasElements = false;
            
            // 遍历所有实体
            entities.forEach(entity => {
                minX = Math.min(minX, entity.x);
                minY = Math.min(minY, entity.y);
                maxX = Math.max(maxX, entity.x + entity.width);
                maxY = Math.max(maxY, entity.y + entity.height);
                hasElements = true;
            });
            
            // 遍历所有属性
            attributes.forEach(attr => {
                minX = Math.min(minX, attr.x - attr.rx);
                minY = Math.min(minY, attr.y - attr.ry);
                maxX = Math.max(maxX, attr.x + attr.rx);
                maxY = Math.max(maxY, attr.y + attr.ry);
                hasElements = true;
            });
            
            // 遍历所有关系
            relationships.forEach(rel => {
                minX = Math.min(minX, rel.x - rel.width / 2);
                minY = Math.min(minY, rel.y - rel.height / 2);
                maxX = Math.max(maxX, rel.x + rel.width / 2);
                maxY = Math.max(maxY, rel.y + rel.height / 2);
                hasElements = true;
            });
            
            // 处理连接线的边界
            relationships.forEach(rel => {
                const fromEntity = entities.find(e => e.id === rel.fromEntityId);
                const toEntity = entities.find(e => e.id === rel.toEntityId);
                if (fromEntity && toEntity) {
                    minX = Math.min(minX, fromEntity.x + fromEntity.width / 2, toEntity.x + toEntity.width / 2);
                    minY = Math.min(minY, fromEntity.y + fromEntity.height / 2, toEntity.y + toEntity.height / 2);
                    maxX = Math.max(maxX, fromEntity.x + fromEntity.width / 2, toEntity.x + toEntity.width / 2);
                    maxY = Math.max(maxY, fromEntity.y + fromEntity.height / 2, toEntity.y + toEntity.height / 2);
                }
            });
            
            // 如果没有元素，使用默认范围
            if (!hasElements || !isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) {
                const gElement = g.node();
                const bbox = gElement.getBBox();
                if (bbox.width > 0 && bbox.height > 0) {
                    minX = bbox.x;
                    minY = bbox.y;
                    maxX = bbox.x + bbox.width;
                    maxY = bbox.y + bbox.height;
                } else {
                    minX = 0;
                    minY = 0;
                    maxX = width;
                    maxY = height;
                }
            }
            
            // 添加边距
            const padding = 50;
            exportBounds = {
                x: minX - padding,
                y: minY - padding,
                width: maxX - minX + padding * 2,
                height: maxY - minY + padding * 2
            };
        }
        
        // 创建新的SVG
        const exportSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        exportSvg.setAttribute('width', exportBounds.width);
        exportSvg.setAttribute('height', exportBounds.height);
        exportSvg.setAttribute('viewBox', `${exportBounds.x} ${exportBounds.y} ${exportBounds.width} ${exportBounds.height}`);
        exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        exportSvg.setAttribute('style', 'background-color: ' + (withBackground ? 'white' : 'transparent'));
        
        // 导出时注入与当前界面一致的字体大小，避免硬编码
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        const { entity: __fontEntity, attr: __fontAttr, rel: __fontRel } = getCurrentFontSizes();
        style.textContent = `
            .entity-text { font-family: Arial, sans-serif; font-size: ${__fontEntity}px; font-weight: 600; fill: black; }
            .attribute-text { font-family: Arial, sans-serif; font-size: ${__fontAttr}px; fill: black; }
            .relationship-text { font-family: Arial, sans-serif; font-size: ${__fontRel}px; font-style: italic; fill: black; }
            .connection-label { font-size: ${__fontRel}px; font-weight: bold; fill: black; }
        `;
        exportSvg.appendChild(style);
        
        // 克隆定义（markers等）
        const defs = svgElement.querySelector('defs');
        if (defs) {
            exportSvg.appendChild(defs.cloneNode(true));
        }
        
        // 添加背景
        if (withBackground) {
            const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            background.setAttribute('x', exportBounds.x);
            background.setAttribute('y', exportBounds.y);
            background.setAttribute('width', exportBounds.width);
            background.setAttribute('height', exportBounds.height);
            background.setAttribute('fill', 'white');
            exportSvg.appendChild(background);
        }
        
        // 克隆g元素及其所有内容
        const gClone = g.node().cloneNode(true);
        gClone.removeAttribute('transform');

        // 将当前字号内联到文本节点（SVG 导出同样处理）
        (function __inlineFontForSVG() {
            const { entity: __fontEntity, attr: __fontAttr, rel: __fontRel } = getCurrentFontSizes();
            const texts = gClone.querySelectorAll('text');
            texts.forEach(t => {
                const cls = t.getAttribute('class') || '';
                let size = __fontAttr;
                let weight = 'normal';
                if (cls.includes('entity-text')) { size = __fontEntity; weight = '600'; }
                else if (cls.includes('relationship-text')) { size = __fontRel; }
                else if (cls.includes('connection-label')) { size = __fontRel; weight = 'bold'; }
                t.setAttribute('font-family', 'Arial, sans-serif');
                t.setAttribute('font-size', String(size));
                if (weight) t.setAttribute('font-weight', weight);
                const styleAttr = t.getAttribute('style') || '';
                const cleaned = styleAttr.replace(/font-size\s*:\s*[^;]+;?/gi, '').replace(/font-weight\s*:\s*[^;]+;?/gi, '');
                t.setAttribute('style', (cleaned + `;font-size:${size}px;${weight ? `font-weight:${weight};` : ''}`).replace(/^;/, ''));
            });
        })();

        exportSvg.appendChild(gClone);
        
        // 导出
        const svgData = new XMLSerializer().serializeToString(exportSvg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.download = filename + '.svg';
        a.href = url;
        a.click();
        URL.revokeObjectURL(url);
        showToast('SVG导出成功！', 'success');
        
    } catch (error) {
        console.error('导出SVG失败:', error);
        alert('导出SVG失败，请稍后重试');
    }
}

/**
 * 更新实体大小的辅助函数
 */
function updateEntitySize() {
    const width = parseInt(document.getElementById('entity-width').value) || 120;
    const height = parseInt(document.getElementById('entity-height').value) || 60;
    
    defaultSizes.entity.width = width;
    defaultSizes.entity.height = height;
    
    // 应用到现有实体
    entities.forEach(entity => {
        entity.width = Math.max(width, calculateEntityWidth(entity.displayName));
        entity.height = height;
    });
    
    renderDiagram();
}

function updateAttributeSize() {
    const rx = parseInt(document.getElementById('attr-width').value) || 60;
    const ry = parseInt(document.getElementById('attr-height').value) || 25;
    
    defaultSizes.attribute.rx = rx;
    defaultSizes.attribute.ry = ry;
    
    // 应用到现有属性
    attributes.forEach(attr => {
        attr.rx = Math.max(rx, calculateAttributeWidth(attr.displayName));
        attr.ry = ry;
    });
    
    renderDiagram();
}

function updateRelationshipSize() {
    const width = parseInt(document.getElementById('rel-width').value) || 80;
    const height = parseInt(document.getElementById('rel-height').value) || 50;
    
    defaultSizes.relationship.width = width;
    defaultSizes.relationship.height = height;
    
    // 应用到现有关系
    relationships.forEach(rel => {
        rel.width = Math.max(width, calculateRelationshipWidth(rel.displayName));
        rel.height = height;
    });
    
    renderDiagram();
}

function applyUniformSize() {
    updateEntitySize();
    updateAttributeSize();
    updateRelationshipSize();
    
    // 重新排列属性
    entities.forEach(entity => {
        arrangeAttributes(entity.id);
    });
    
    renderDiagram();
    console.log('已应用统一大小设置');
}

// --- 可能缺失的辅助函数 ---
// The following functions are called but were not found in the corrupted file.
// I will add them back based on our previous work.

/**
 * 更新侧边栏的实体列表
 */
function updateEntityList() {
    const list = document.getElementById('entity-list');
    if (!list) return;
    list.innerHTML = '';
    
    // 如果没有实体，显示提示信息
    if (entities.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'empty-state';
        emptyDiv.innerHTML = `
            <i class="fas fa-database fa-2x"></i>
            <p>暂无实体</p>
            <button class="btn btn-sm btn-primary" onclick="importSQL()">
                <i class="fas fa-plus"></i> 导入SQL
            </button>
        `;
        list.appendChild(emptyDiv);
        return;
    }
    
    // 显示实体统计信息
    const statsDiv = document.createElement('div');
    statsDiv.className = 'entity-stats';
    const totalAttrs = attributes.length;
    const totalRels = relationships.length;
    statsDiv.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">实体:</span>
            <span class="stat-value">${entities.length}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">属性:</span>
            <span class="stat-value">${totalAttrs}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">关系:</span>
            <span class="stat-value">${totalRels}</span>
        </div>
    `;
    list.appendChild(statsDiv);
    
    // 添加搜索框
    const searchDiv = document.createElement('div');
    searchDiv.className = 'entity-search';
    searchDiv.innerHTML = `
        <input type="text" id="entity-search-input" placeholder="搜索实体..." class="form-control">
    `;
    list.appendChild(searchDiv);
    
    // 创建实体列表容器
    const entitiesContainer = document.createElement('div');
    entitiesContainer.className = 'entities-container';
    list.appendChild(entitiesContainer);
    
    // 渲染每个实体
    entities.forEach(entity => {
        const entityAttrs = attributes.filter(attr => attr.entityId === entity.id);
        const entityRels = relationships.filter(rel => 
            rel.fromEntityId === entity.id || rel.toEntityId === entity.id
        );
        
        const entityItem = document.createElement('div');
        entityItem.className = 'entity-item';
        entityItem.dataset.entityId = entity.id;
        entityItem.dataset.entityName = entity.displayName.toLowerCase();
        
        // 实体头部
        const header = document.createElement('div');
        header.className = 'entity-item-header';
        header.innerHTML = `
            <div class="entity-main-info">
                <span class="entity-item-name">${entity.displayName}</span>
                <div class="entity-summary">
                    <span class="entity-badge"><i class="fas fa-list"></i> ${entityAttrs.length} 属性</span>
                    <span class="entity-badge"><i class="fas fa-link"></i> ${entityRels.length} 关系</span>
                </div>
            </div>
            <div class="entity-actions">
                <button class="icon-btn" title="定位实体" onclick="focusEntity('${entity.id}')">
                    <i class="fas fa-crosshairs"></i>
                </button>
                <button class="icon-btn" title="展开/收起" onclick="toggleEntityDetail('${entity.id}')">
                    <i class="fas fa-chevron-down"></i>
                </button>
            </div>
        `;
        entityItem.appendChild(header);
        
        // 实体详情（默认隐藏）
        const details = document.createElement('div');
        details.className = 'entity-item-details';
        details.id = `entity-details-${entity.id}`;
        details.style.display = 'none';
        
        // 属性列表
        if (entityAttrs.length > 0) {
            const attrSection = document.createElement('div');
            attrSection.className = 'detail-section';
            attrSection.innerHTML = '<h4>属性:</h4>';
            const attrList = document.createElement('ul');
            attrList.className = 'attribute-list';
            
            entityAttrs.forEach(attr => {
                const attrItem = document.createElement('li');
                attrItem.className = 'attribute-item';
                attrItem.innerHTML = `
                    <span class="attr-name ${attr.isPK ? 'primary-key' : ''} ${attr.isFK ? 'foreign-key' : ''}">
                        ${attr.isPK ? '<i class="fas fa-key"></i> ' : ''}
                        ${attr.isFK ? '<i class="fas fa-link"></i> ' : ''}
                        ${attr.displayName}
                    </span>
                    <span class="attr-type">${attr.type}</span>
                `;
                attrItem.onclick = () => focusAttribute(attr.id);
                attrList.appendChild(attrItem);
            });
            
            attrSection.appendChild(attrList);
            details.appendChild(attrSection);
        }
        
        // 关系列表
        if (entityRels.length > 0) {
            const relSection = document.createElement('div');
            relSection.className = 'detail-section';
            relSection.innerHTML = '<h4>关系:</h4>';
            const relList = document.createElement('ul');
            relList.className = 'relation-list';
            
            entityRels.forEach(rel => {
                const relItem = document.createElement('li');
                relItem.className = 'relation-item';
                const otherEntityId = rel.fromEntityId === entity.id ? rel.toEntityId : rel.fromEntityId;
                const otherEntity = entities.find(e => e.id === otherEntityId);
                const direction = rel.fromEntityId === entity.id ? '→' : '←';
                
                relItem.innerHTML = `
                    <span class="rel-type">${rel.type}</span>
                    <span class="rel-target">${direction} ${otherEntity ? otherEntity.displayName : '未知'}</span>
                `;
                relItem.onclick = () => focusRelationship(rel.id);
                relList.appendChild(relItem);
            });
            
            relSection.appendChild(relList);
            details.appendChild(relSection);
        }
        
        entityItem.appendChild(details);
        entitiesContainer.appendChild(entityItem);
    });
    
    // 添加搜索功能
    const searchInput = document.getElementById('entity-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const items = entitiesContainer.querySelectorAll('.entity-item');
            
            items.forEach(item => {
                const name = item.dataset.entityName;
                if (name.includes(searchTerm)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
}

/**
 * 视图缩放以适应所有元素
 */
function zoomFit() {
    if (entities.length === 0) return;
    
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    g.selectAll('.entity, .attribute, .relationship').each(function(d) {
        const bbox = this.getBBox();
        const [x, y] = [d.x, d.y];
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x + bbox.width);
        maxY = Math.max(maxY, y + bbox.height);
    });
    
    const boundsWidth = maxX - minX;
    const boundsHeight = maxY - minY;
    if (boundsWidth === 0 || boundsHeight === 0) return;
    
    const fullWidth = width;
    const fullHeight = height;
    const midX = minX + boundsWidth / 2;
    const midY = minY + boundsHeight / 2;
    const scale = Math.min(fullWidth / boundsWidth, fullHeight / boundsHeight) * 0.9;
    const transform = d3.zoomIdentity
        .translate(fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY)
        .scale(scale);
    
    svg.transition().duration(750).call(zoom.transform, transform);
}

/**
 * 聚焦到指定实体
 */
function focusEntity(entityId) {
    const entity = entities.find(e => e.id === entityId);
    if (!entity) return;
    
    // 高亮实体
    g.selectAll('.entity').classed('highlighted', false);
    g.select(`#${entityId}`).classed('highlighted', true);
    
    // 居中显示
    const transform = d3.zoomIdentity
        .translate(width / 2 - entity.x * 1.5, height / 2 - entity.y * 1.5)
        .scale(1.5);
    svg.transition().duration(750).call(zoom.transform, transform);
    
    // 高亮侧边栏项目
    document.querySelectorAll('.entity-item').forEach(item => {
        item.classList.remove('highlighted');
    });
    const listItem = document.querySelector(`[data-entity-id="${entityId}"]`);
    if (listItem) {
        listItem.classList.add('highlighted');
        listItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

/**
 * 聚焦到指定属性
 */
function focusAttribute(attrId) {
    const attr = attributes.find(a => a.id === attrId);
    if (!attr) return;
    
    // 高亮属性
    g.selectAll('.attribute').classed('highlighted', false);
    g.select(`#${attrId}`).classed('highlighted', true);
    
    // 居中显示
    const transform = d3.zoomIdentity
        .translate(width / 2 - attr.x * 1.5, height / 2 - attr.y * 1.5)
        .scale(1.5);
    svg.transition().duration(750).call(zoom.transform, transform);
}

/**
 * 聚焦到指定关系
 */
function focusRelationship(relId) {
    const rel = relationships.find(r => r.id === relId);
    if (!rel) return;
    
    // 高亮关系
    g.selectAll('.relationship').classed('highlighted', false);
    g.select(`#${relId}`).classed('highlighted', true);
    
    // 居中显示
    const transform = d3.zoomIdentity
        .translate(width / 2 - rel.x * 1.5, height / 2 - rel.y * 1.5)
        .scale(1.5);
    svg.transition().duration(750).call(zoom.transform, transform);
}

/**
 * 展开/收起实体详情
 */
function toggleEntityDetail(entityId) {
    const details = document.getElementById(`entity-details-${entityId}`);
    const entityItem = document.querySelector(`[data-entity-id="${entityId}"]`);
    const chevron = entityItem.querySelector('.fa-chevron-down, .fa-chevron-up');
    
    if (details) {
        if (details.style.display === 'none') {
            details.style.display = 'block';
            entityItem.classList.add('expanded');
            if (chevron) {
                chevron.classList.remove('fa-chevron-down');
                chevron.classList.add('fa-chevron-up');
            }
        } else {
            details.style.display = 'none';
            entityItem.classList.remove('expanded');
            if (chevron) {
                chevron.classList.remove('fa-chevron-up');
                chevron.classList.add('fa-chevron-down');
            }
        }
    }
}

/**
 * 显示模态框
 * @param {string} modalId 
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * 关闭模态框
 * @param {string} modalId 
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
            modal.style.display = 'none';
        }
    }


// --- 文档导出功能 ---

/**
 * 显示导出文档的模态框
 */
function showExportDocModal() {
    const sql = sqlEditor.getValue();
    if (!sql.trim()) {
        importSQL(); // 如果编辑器是空的，先弹出导入框
        return;
    }
    document.getElementById('doc-preview-content').innerHTML = '<p>请选择格式并点击生成...</p>';
    showModal('export-doc-modal');
}

/**
 * 执行文档导出
 */
async function exportDoc() {
    const sql = sqlEditor.getValue();
    const format = document.querySelector('input[name="export-format"]:checked').value;
    const previewContent = document.getElementById('doc-preview-content');
    previewContent.innerHTML = '<div class="loader"></div><p>正在生成文档，请稍候...</p>';

    try {
        const response = await fetch('/api/generate_doc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, format })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || '生成失败');
        }

        if (format === 'html') {
            const data = await response.json();
            // 关闭当前模态框
            closeModal('export-doc-modal');
            // 在iframe中显示HTML预览
            showHTMLPreview(data.html);
        } else if (format === 'docx') {
            previewContent.innerHTML = '<p>请求成功！您的Word文档正在下载...</p>';
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
            a.style.display = 'none';
                a.href = url;
            a.download = 'database-design.docx';
                document.body.appendChild(a);
                a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            setTimeout(() => closeModal('export-doc-modal'), 2000);
    }
    } catch (error) {
        previewContent.innerHTML = `<p style="color: red;">错误: ${error.message}</p>`;
    }
}

/**
 * 在iframe中显示HTML预览
 * @param {string} htmlContent HTML内容
 */
function showHTMLPreview(htmlContent) {
    const iframe = document.getElementById('html-preview-frame');
    if (iframe) {
        // 创建完整的HTML文档
        const fullHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库文档预览</title>
</head>
<body style="margin: 0; padding: 0;">
    ${htmlContent}
</body>
</html>`;

        // 使用data URL在iframe中显示内容
        const dataURL = 'data:text/html;charset=utf-8,' + encodeURIComponent(fullHTML);
        iframe.src = dataURL;

        // 显示HTML预览模态框
        showModal('html-preview-modal');
    }
}

// --- 项目管理功能 ---

/**
 * 显示项目管理模态框
 */
async function showProjectModal() {
    showModal('project-modal');
    await loadProjectList();
}

/**
 * 切换项目标签页
 */
function switchProjectTab(tab) {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    
    // 这里可以根据不同的标签页加载不同的项目列表
    loadProjectList(tab);
}

/**
 * 加载项目列表
 */
async function loadProjectList(tab = 'recent') {
    const loader = showLoading('加载项目列表...');
    
    try {
        const response = await fetch('/api/list_projects');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '加载失败');
        }
        
        const projectList = document.getElementById('project-list');
        const projects = tab === 'recent' ? data.recent : data.projects;
        
        if (projects.length === 0) {
            projectList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open fa-3x"></i>
                    <p>暂无项目</p>
                </div>
            `;
        } else {
            projectList.innerHTML = projects.map(project => `
                <div class="project-item">
                    <div class="project-info">
                        <div class="project-name">${project.name}</div>
                        <div class="project-date">更新于: ${formatDate(project.updated_at)}</div>
                    </div>
                    <div class="project-actions">
                        <button class="btn-load" onclick="loadProject('${project.id}')">
                            <i class="fas fa-folder-open"></i> 打开
                        </button>
                        <button class="btn-delete" onclick="deleteProject('${project.id}')">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
    } catch (error) {
        showToast('加载项目列表失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

/**
 * 保存项目
 */
async function saveProject() {
    const projectName = currentProjectName || prompt('请输入项目名称:', `项目_${new Date().toLocaleString()}`);
    if (!projectName) return;
    
    const loader = showLoading('保存项目...');
    
    try {
        // 准备项目数据
        const projectData = {
            project_id: currentProjectId,
            name: projectName,
            sql: sqlEditor.getValue(),
            entities: entities.map(e => ({
                id: e.id,
                name: e.name,
                displayName: e.displayName,
                x: e.x,
                y: e.y,
                width: e.width,
                height: e.height
            })),
            relationships: relationships.map(r => ({
                id: r.id,
                name: r.name,
                displayName: r.displayName,
                fromEntityId: r.fromEntityId,
                toEntityId: r.toEntityId,
                type: r.type,
                x: r.x,
                y: r.y,
                width: r.width,
                height: r.height
            }))
        };
        
        // 保存属性数据
        projectData.entities.forEach(entity => {
            entity.attributes = attributes
                .filter(a => a.entityId === entity.id)
                .map(a => ({
                    id: a.id,
                    name: a.name,
                    displayName: a.displayName,
                    type: a.type,
                    isPK: a.isPK,
                    isFK: a.isFK,  // 新增外键标识
                    comment: a.comment,
                    x: a.x,
                    y: a.y,
                    rx: a.rx,
                    ry: a.ry
                }));
        });
        
        const response = await fetch('/api/save_project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || '保存失败');
        }
        
        currentProjectId = result.project_id;
        currentProjectName = projectName;
        
        showToast('项目保存成功', 'success');
        
    } catch (error) {
        showToast('保存项目失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

/**
 * 加载项目
 */
async function loadProject(projectId) {
    const loader = showLoading('加载项目...');
    
    try {
        const response = await fetch(`/api/load_project/${projectId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '加载失败');
        }
        
        const project = data.project;
        
        // 清空当前数据
        entities = [];
        attributes = [];
        relationships = [];
        
        // 设置SQL
        sqlEditor.setValue(project.sql || '');
        sqlEditor.clearSelection();
        
        // 恢复实体和属性
        project.entities.forEach(entityData => {
            const entity = new EREntity(
                entityData.name,
                entityData.x,
                entityData.y,
                entityData.displayName
            );
            entity.id = entityData.id;
            entity.width = entityData.width;
            entity.height = entityData.height;
            entities.push(entity);
            
            // 恢复属性
            if (entityData.attributes) {
                entityData.attributes.forEach(attrData => {
                    const attr = new ERAttribute(
                        attrData.name,
                        attrData.type,
                        entity.id,
                        attrData.isPK,
                        attrData.isFK,  // 新增外键标识
                        attrData.displayName,
                        attrData.comment
                    );
                    attr.id = attrData.id;
                    attr.x = attrData.x;
                    attr.y = attrData.y;
                    attr.rx = attrData.rx;
                    attr.ry = attrData.ry;
                    attributes.push(attr);
                });
            }
        });
        
        // 恢复关系
        project.relationships.forEach(relData => {
            const rel = new ERRelationship(
                relData.name,
                relData.fromEntityId,
                relData.toEntityId,
                relData.type,
                relData.displayName
            );
            rel.id = relData.id;
            rel.x = relData.x;
            rel.y = relData.y;
            rel.width = relData.width;
            rel.height = relData.height;
            relationships.push(rel);
        });
        
        // 更新当前项目信息
        currentProjectId = project.id;
        currentProjectName = project.name;
        
        // 重新渲染
        renderDiagram();
        updateEntityList();
        
        // 关闭模态框
        closeModal('project-modal');
        
        showToast(`项目 "${project.name}" 加载成功`, 'success');
        
    } catch (error) {
        showToast('加载项目失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

/**
 * 删除项目
 */
async function deleteProject(projectId) {
    if (!confirm('确定要删除这个项目吗？此操作不可撤销。')) {
        return;
    }
    
    const loader = showLoading('删除项目...');
    
    try {
        const response = await fetch(`/api/delete_project/${projectId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || '删除失败');
        }
        
        // 如果删除的是当前项目，清空项目ID
        if (projectId === currentProjectId) {
            currentProjectId = null;
            currentProjectName = null;
        }
        
        // 重新加载项目列表
        await loadProjectList();
        
        showToast('项目删除成功', 'success');
        
    } catch (error) {
        showToast('删除项目失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 向后兼容的导出图片函数
 */
function exportImage() {
    showExportImageModal();
}

// ==================== 简化ER图功能 ====================

// 简化SQL编辑器实例
let simplifiedSqlEditor = null;

/**
 * 打开简化ER图生成模态框
 */
function generateSimplifiedER() {
    // 初始化简化SQL编辑器
    if (!simplifiedSqlEditor) {
        setTimeout(() => {
            simplifiedSqlEditor = ace.edit('simplified-sql-editor');
            simplifiedSqlEditor.setTheme('ace/theme/monokai');
            simplifiedSqlEditor.session.setMode('ace/mode/sql');
            simplifiedSqlEditor.setOptions({
                fontSize: '14px',
                showPrintMargin: false,
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true
            });
            
            // 如果有当前的SQL内容，填充进去
            if (sqlEditor && sqlEditor.getValue()) {
                simplifiedSqlEditor.setValue(sqlEditor.getValue());
                simplifiedSqlEditor.clearSelection();
            }
        }, 100);
    } else {
        // 如果编辑器已存在，同步当前SQL内容
        if (sqlEditor && sqlEditor.getValue()) {
            simplifiedSqlEditor.setValue(sqlEditor.getValue());
            simplifiedSqlEditor.clearSelection();
        }
    }
    
    showModal('simplified-er-modal');
}

/**
 * 执行简化ER图生成
 */
async function executeSimplifiedGeneration() {
    const sql = simplifiedSqlEditor ? simplifiedSqlEditor.getValue() : '';
    if (!sql.trim()) {
        showToast('请输入SQL语句', 'warning');
        return;
    }
    
    // 获取简化选项
    const options = {
        showMainEntities: document.getElementById('show-main-entities').checked,
        groupFunctions: document.getElementById('group-functions').checked,
        hideAttributes: document.getElementById('hide-attributes').checked,
        paperStyle: document.getElementById('paper-style').checked,
        usagePurpose: document.getElementById('usage-purpose').value
    };
    
    const loader = showLoading('AI正在分析SQL并生成简化ER图...<br><small>复杂SQL分析需要更多时间，请耐心等待</small>');
    
    try {
        const response = await fetch('/api/generate_simplified_er', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sql: sql,
                options: options
            })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '生成失败');
        }
        
        // 清空当前图表
        entities = [];
        attributes = [];
        relationships = [];
        
        // 应用简化的ER数据
        applySimplifiedERData(data);
        
        // 关闭模态框
        closeModal('simplified-er-modal');
        
        // 自动布局
        setTimeout(() => {
            autoLayout();
            
            // 检查是否是AI生成的结果还是默认简化结果
            if (data.entities && data.entities.length > 0) {
                if (data.ai_generated === false) {
                    showToast('AI服务暂时繁忙，已为您生成基础简化ER图', 'warning');
                } else {
                    showToast('AI简化ER图生成成功！', 'success');
                }
            } else {
                showToast('简化ER图生成完成', 'success');
            }
        }, 100);
        
    } catch (error) {
        showToast('生成简化ER图失败: ' + error.message, 'error');
    } finally {
        hideLoading(loader);
    }
}

/**
 * 应用简化的ER图数据
 */
function applySimplifiedERData(data) {
    // 处理实体
    data.entities.forEach((entityData, index) => {
        const entity = new EREntity(
            entityData.name,
            200 + (index % 3) * 250,
            100 + Math.floor(index / 3) * 200,
            entityData.displayName
        );
        
        // 为简化ER图调整实体样式
        entity.simplified = true;
        entities.push(entity);
        
        // 如果不隐藏属性，添加关键属性
        if (!data.options?.hideAttributes && entityData.attributes) {
            entityData.attributes.forEach((attrData) => {
                const attr = new ERAttribute(
                    attrData.name, 
                    attrData.type, 
                    entity.id, 
                    attrData.isPK, 
                    attrData.isFK,
                    attrData.displayName, 
                    attrData.comment
                );
                attributes.push(attr);
            });
            arrangeAttributes(entity.id);
        }
    });
    
    // 处理关系
    data.relationships.forEach(relData => {
        const fromEntity = entities.find(e => e.name === relData.from);
        const toEntity = entities.find(e => e.name === relData.to);
        
        if (fromEntity && toEntity) {
            const rel = new ERRelationship(
                relData.name,
                fromEntity.id,
                toEntity.id,
                relData.type || '1:N',
                relData.displayName
            );
            relationships.push(rel);
        }
    });
    
         // 重新渲染
    renderDiagram();
}

/**
 * 为简化ER图排列属性（只显示关键属性）
 */
function arrangeAttributesSimplified(entityId) {
    const entity = entities.find(e => e.id === entityId);
    if (!entity) return;
    
    const entityAttrs = attributes.filter(a => a.entityId === entityId);
    
    // 只显示主键和重要属性
    const keyAttrs = entityAttrs.filter(a => a.isPK || a.isFK);
    
    // 简化的圆形排列
    const radius = Math.max(80, entity.width * 0.6);
    const angleStep = (2 * Math.PI) / Math.max(keyAttrs.length, 1);
    
    keyAttrs.forEach((attr, index) => {
        const angle = index * angleStep - Math.PI / 2;
        attr.x = entity.x + entity.width / 2 + radius * Math.cos(angle);
        attr.y = entity.y + entity.height / 2 + radius * Math.sin(angle);
    });
}