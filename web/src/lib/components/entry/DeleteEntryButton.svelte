<script lang="ts">
	import { tick } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import { uiStore } from '$lib/stores/ui.svelte';

	interface Props {
		entryId: string;
		kbName: string;
		entryTitle: string;
		onDeleted: () => void;
	}

	let { entryId, kbName, entryTitle, onDeleted }: Props = $props();

	let confirming = $state(false);
	let deleting = $state(false);
	let confirmButton = $state<HTMLButtonElement | null>(null);
	let deleteButton = $state<HTMLButtonElement | null>(null);

	async function startConfirm() {
		confirming = true;
		// Focus moves to the confirm step when it opens, so keyboard users
		// are not left focused on a button that no longer does anything.
		await tick();
		confirmButton?.focus();
	}

	async function cancel() {
		confirming = false;
		await tick();
		deleteButton?.focus();
	}

	async function confirmDelete() {
		if (deleting) return;
		deleting = true;
		try {
			await api.deleteEntry(entryId, kbName);
			uiStore.toast('Entry deleted', 'success');
			onDeleted();
			// No re-enable here: the page navigates away and unmounts this
			// component, so there is no window in which a second click could
			// fire a second DELETE against an entry that is already gone.
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) {
				// Already deleted (another tab, another client): the reader's
				// goal is achieved; say so and leave the entry page.
				uiStore.toast('Entry was already deleted', 'info');
				onDeleted();
				return;
			}
			const reason = e instanceof ApiError && e.detail ? e.detail : '';
			uiStore.toast(reason ? `Could not delete: ${reason}` : 'Could not delete entry', 'error');
			deleting = false;
			confirming = false;
			await tick();
			deleteButton?.focus();
		}
	}
</script>

<!-- Delete stays where it was, disabled, for the whole confirm step: the second
     click of a double-click must land on a disabled button, never on a Confirm
     that replaced Delete in its slot. -->
<button
	bind:this={deleteButton}
	onclick={startConfirm}
	disabled={confirming || deleting}
	class="rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-50 dark:border-zinc-600"
>
	Delete
</button>
{#if confirming}
	<span
		class="inline-block max-w-64 truncate text-sm text-zinc-600 dark:text-zinc-400"
	>
		Delete “{entryTitle}” from {kbName}?
	</span>
	<button
		bind:this={confirmButton}
		onclick={confirmDelete}
		disabled={deleting}
		class="rounded-md border border-red-600 bg-red-600 px-3 py-1 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
	>
		{deleting ? 'Deleting...' : 'Confirm delete'}
	</button>
	<button
		onclick={cancel}
		disabled={deleting}
		class="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-600"
	>
		Cancel
	</button>
{/if}
