/**
 * Prompt 基础信息详情弹窗。
 */
import { h } from '../lib/preact.mjs';
import { buildImageUrl } from '../utils.js';
import { Dialog } from './Dialog.js';
import { Icon } from '../lib/icons.mjs';

export function PromptInfoDialog({ isOpen, prompt, onClose }) {
  if (!prompt) return null;

  const name = prompt.name || prompt.value;
  const fields = [
    ['名称', name],
    ['Prompt Value', prompt.value],
    ['别名', prompt.alias || '—'],
  ];

  return h(Dialog, {
    isOpen,
    onClose,
    title: 'Prompt 详情',
    titleIcon: h(Icon, { name: 'info-circle', size: 17 }),
    maxWidth: '880px',
    maxHeight: '80vh',
    className: 'prompt-info-dialog',
  }, h('div', { class: 'prompt-info-content' }, [
    h('div', { class: 'prompt-info-cover' }, prompt.coverImagePath
      ? h('img', { src: buildImageUrl(prompt.coverImagePath), alt: name })
      : h('div', { class: 'prompt-info-cover-empty' }, [
        h(Icon, { name: 'image', size: 36 }),
        h('span', {}, '暂无封面图片'),
      ])),
    h('dl', { class: 'prompt-info-fields' }, fields.map(([label, value]) => [
      h('dt', { key: `${label}-label` }, label),
      h('dd', { key: `${label}-value`, title: value }, value),
    ])),
  ]));
}
