export default function rehypeWrapTables() {
	return (tree) => {
		wrapTables(tree);
	};
}

function wrapTables(node) {
	if (!Array.isArray(node.children)) return;

	for (let index = 0; index < node.children.length; index += 1) {
		const child = node.children[index];

		if (child.type === 'element' && child.tagName === 'table') {
			node.children[index] = {
				type: 'element',
				tagName: 'div',
				properties: { className: ['table-scroll'], tabIndex: 0 },
				children: [child],
			};
			continue;
		}

		wrapTables(child);
	}
}
