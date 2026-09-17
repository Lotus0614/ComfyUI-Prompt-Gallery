/**
 * Prompt 基础信息详情弹窗。
 * 布局：左侧封面图尽量撑满高度，右侧字段列独立滚动。
 */
import { h } from '../lib/preact.mjs';
import { useState, useEffect, useCallback } from '../lib/hooks.mjs';
import { buildImageUrl } from '../utils.js';
import { Dialog } from './Dialog.js';
import { Icon } from '../lib/icons.mjs';
import { showToast } from './Toast.js';

export function PromptInfoDialog({ isOpen, prompt, onClose }) {
  const [copied, setCopied] = useState(false);

  // 切换 Prompt 或重新打开时重置复制反馈
  useEffect(() => {
    setCopied(false);
  }, [prompt?.value, isOpen]);

  const handleCopyValue = useCallback(() => {
    const text = prompt?.value || '';
    if (!text) return;
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
        showToast('已复制 Prompt Value', 'success');
      })
      .catch(() => showToast('复制失败', 'error'));
  }, [prompt]);

  if (!prompt) return null;

  const name = prompt.name || prompt.value;
  const fields = [
    { label: '名称', value: name },
    { label: 'Prompt Value', value: prompt.value, copyable: true },
    { label: '别名', value: prompt.alias || '—' },
  ];

  return h(Dialog, {
    isOpen,
    onClose,
    title: 'Prompt 详情',
    titleIcon: h(Icon, { name: 'info-circle', size: 17 }),
    maxWidth: '1000px',
    maxHeight: '88vh',
    className: 'prompt-info-dialog',
  }, h('div', { class: 'prompt-info-content' }, [
    h('div', { class: 'prompt-info-cover' }, prompt.coverImagePath
      ? h('img', { src: buildImageUrl(prompt.coverImagePath), alt: name })
      : h('div', { class: 'prompt-info-cover-empty' }, [
        h(Icon, { name: 'image', size: 36 }),
        h('span', {}, '暂无封面图片'),
      ])),
    h('dl', { class: 'prompt-info-fields' }, fields.map(({ label, value, copyable }) => [
      h('dt', { key: `${label}-label` }, [
        h('span', {}, label),
        copyable &&
          h(
            'button',
            {
              class: `prompt-info-copy-btn${copied ? ' copied' : ''}`,
              type: 'button',
              title: copied ? '已复制' : '复制 Prompt Value',
              'aria-label': '复制 Prompt Value',
              onClick: handleCopyValue,
            },
            h(Icon, { name: copied ? 'check' : 'copy', size: 13 }),
          ),
      ]),
      h('dd', { key: `${label}-value`, title: value }, value),
    ])),
  ]));
}
