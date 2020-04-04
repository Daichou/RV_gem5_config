
CC:=riscv64-unknown-elf-gcc
exe:=dhrystone
obj:=dhrystone_main.o dhrystone.o
all:$(obj)
	$(CC) -o $(exe) $(obj)
%.o:%.c
	$(CC) -c $^ -o $@

.PHONY:clean
clean:
	rm -rf $(obj) $(exe)
