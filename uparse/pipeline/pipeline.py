from typing import (
    AsyncGenerator,
    Generic,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

import anyio
from typing_extensions import TypedDict

from uparse.schema import Document

from .schema import SharedResource


class State(TypedDict, total=False):
    uri: str
    doc: Document


StateType = TypeVar("StateType", bound=State)


class TransformListener(Generic[StateType]):
    async def on_transform_enter(self, transform: "BaseTransform", state: StateType):
        pass

    async def on_transform_exit(self, transform: "BaseTransform", state: StateType):
        pass


class TranformBatchListener:
    def __init__(self, listeners: list[TransformListener], run_in_background: bool = False):
        if listeners is None:
            listeners = []
        self.listeners = listeners
        self.run_in_background = run_in_background

    def _on_event_construct(self, event: str):
        async def _on_event(*args):
            if not self.listeners:
                return
            if self.run_in_background:
                async with anyio.create_task_group() as tg:
                    for listener in self.listeners:
                        tg.start_soon(listener.__getattribute__(event), *args)
            else:
                for listener in self.listeners:
                    await listener.__getattribute__(event)(*args)

        return _on_event

    def __getattribute__(self, name: str):
        if name.startswith("on_"):
            return self._on_event_construct(name)
        return super().__getattribute__(name)

    def add_listener(self, listener: TransformListener):
        self.listeners.append(listener)

    def remove_listener(self, listener: TransformListener):
        self.listeners.remove(listener)

    def clear_listeners(self):
        self.listeners = []


class BaseTransform(Generic[StateType]):
    def __init__(
        self,
        transforms: Optional[List["BaseTransform"]] = None,
        dependencies: Optional[List[str]] = None,
        run_in_parallel: bool = False,
        run_type: Literal["before", "after", "ignore"] = "ignore",
        input_key: Optional[Union[List[str], str]] = None,
        output_key: Optional[Union[List[str], str]] = None,
        listeners: list[TransformListener] | None = None,
        shared: Optional[SharedResource] = None,
        callback_name: str = "transform",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name = self.__class__.__name__
        self.input_key = input_key
        self.output_key = output_key
        self.shared = shared

        self._dependencies = dependencies
        self._transforms = transforms
        self._run_in_parallel = run_in_parallel
        self._run_type = run_type
        if self._run_type == "ignore" and self._transforms is None:
            self._run_type = "after"
        self._inited = False
        self._callback_name = callback_name
        self._enter_callback = f"on_{self._callback_name}_enter"
        self._exit_callback = f"on_{self._callback_name}_exit"
        self._listeners = listeners

    async def _init_sub_transforms(self):
        _to_init = [v for v in self.__dict__.values() if isinstance(v, BaseTransform)]
        if self._transforms is not None:
            _to_init = _to_init + self._transforms
        async with anyio.create_task_group() as tg:
            for t in _to_init:
                t.name = f"{self.name}::{t.name}"
                tg.start_soon(t._init, self.shared)

    def _default_sharedresource(self):
        return SharedResource(listener=TranformBatchListener(self._listeners or []))

    async def _init(self, shared: SharedResource | None = None):
        if self._inited:
            return
        if self.shared is None and shared is None:
            shared = self._default_sharedresource()
        self.shared = shared or self.shared
        await self._init_sub_transforms()
        self._inited = True

    def _get_input(self, state: StateType):
        if isinstance(self.input_key, list):
            return {k: state.get(k) for k in self.input_key}
        else:
            return {self.input_key: state.get(self.input_key)}

    async def _run_sub_transforms(self, state: StateType, *args) -> StateType:
        if self._transforms is None:
            return state
        if self._run_in_parallel:
            async with anyio.create_task_group() as tg:
                for t in self._transforms:
                    tg.start_soon(t.__call__, state, *args)
        else:
            for t in self._transforms:
                state = await t.__call__(state, *args)
        return state

    async def _run_sub_streams(self, state: StateType, *args) -> AsyncGenerator[StateType, None]:
        if self._transforms is None:
            return
        if self._run_in_parallel:
            async with anyio.create_task_group() as tg:
                for t in self._transforms:
                    tg.start_soon(t.__call__, state, *args)
            yield state
            return
        else:
            for t in self._transforms:
                async for s in t.stream(state, *args):
                    yield s

    async def __call__(
        self, state: StateType, listeners: list[TransformListener] | None = None, **kwargs
    ) -> StateType:
        await self._init()
        if listeners:
            listener = TranformBatchListener(listeners)
        else:
            listener = self.shared.listener

        await getattr(listener, self._enter_callback)(self, state)
        if self._run_type == "before":
            state = await self.transform(state, **kwargs)
        state = await self._run_sub_transforms(state, listeners)
        if self._run_type == "after":
            state = await self.transform(state, **kwargs)
        await getattr(listener, self._exit_callback)(self, state)
        return state

    async def stream(
        self, state: StateType, listeners: list[TransformListener] | None = None, **kwargs
    ) -> AsyncGenerator[StateType, None]:
        await self._init()
        if listeners:
            listener = TranformBatchListener(listeners)
        else:
            listener = self.shared.listener

        await getattr(listener, self._enter_callback)(self, state)
        if self._run_type == "before":
            async for s in self.stream_transform(state, **kwargs):
                yield s
        async for s in self._run_sub_streams(state, listeners):
            yield s
        if self._run_type == "after":
            async for s in self.stream_transform(state, **kwargs):
                yield s
        await getattr(listener, self._exit_callback)(self, state)
        return

    async def transform(self, state: StateType, **kwargs) -> StateType:
        return state

    async def stream_transform(self, state: StateType, **kwargs) -> AsyncGenerator[StateType, None]:
        yield await self.transform(state)

    def __or__(self, transform: "BaseTransform") -> "Pipeline[StateType]":
        assert isinstance(transform, BaseTransform), "Only BaseTransform can be piped"
        return Pipeline[StateType](transforms=[self, transform])


class Pipeline(BaseTransform[StateType]):
    allowed_extensions = set()

    def __init__(self, models: dict = {}, batch_size: int = 32, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared = SharedResource(
            batch_size=batch_size,
            listener=TranformBatchListener(self._listeners or []), **models
        )

    def __or__(self, transform: "BaseTransform") -> "Pipeline[StateType]":
        assert isinstance(transform, BaseTransform), "Only BaseTransform can be piped"
        self._transforms.append(transform)
        return self
